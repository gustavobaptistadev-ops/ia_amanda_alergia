"""Orquestração do atendimento: intenção, contexto, ferramentas e resposta."""

import datetime
import json
import logging
import os
import re
from collections.abc import Sequence
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.core.booking_state import (
    booking_is_active,
    booking_next_action,
    mark_booking_created,
    set_offered_slots,
    update_booking_state,
    validate_booking_state,
)
from app.core.clinic_location import clinic_location_text
from app.core.conversation_router import (
    extract_requested_date,
    route_message,
)
from app.core.patient_data import extract_cpf_from_text, extract_latest_cpf
from app.core.prompt_master import (
    PROMPT_INTERPRET,
    PROMPT_FALLBACK,
    MSG_CANCELLATION,
    MSG_RESCHEDULING,
    MSG_HANDOFF,
    MSG_URGENCY,
    MSG_OFF_TOPIC,
    PersonaBuilder,
)
from app.core.input_shield import detect_adversarial_attempt, sanitize_and_wrap_user_input
from app.core.rag import retrieve_context
from app.services.google_calendar import (
    cancel_event,
    check_availability,
    confirm_event,
    create_event,
    reschedule_event,
)

logger = logging.getLogger(__name__)

# Checkpointer global para manter a memória enquanto o servidor estiver rodando
memory = MemorySaver()

from langgraph.graph.message import add_messages


from app.core.state import AgentState

from app.core.graph_nodes.anamnesis_node import clinical_triage_node
from app.core.graph_nodes.rag_node import fetch_context_node
from app.core.graph_nodes.booking_node import schedule_flow_node



from app.api.endpoints.settings import load_config
from app.core.response_quality import assess_response_quality


def get_llm():
    """Inicializa a LLM com a configuração persistida da aplicação."""
    cfg = load_config()
    model_name = cfg.get("model", "gpt-4o-mini")
    temp = float(cfg.get("temperature", 0.65))
    return ChatOpenAI(model=model_name, temperature=temp)


tools = [check_availability, create_event, cancel_event, reschedule_event, confirm_event]


def _interpret_initial_messages(messages: Sequence[BaseMessage]) -> dict:
    """Usa a LLM como intérprete sem delegar a ela o controle do fluxo."""
    transcript = "\n".join(
        f"{'PACIENTE' if getattr(message, 'type', '') == 'human' else 'AMANDA'}: "
        f"{getattr(message, 'content', '')}"
        for message in list(messages)[-8:]
        if getattr(message, "content", "")
    )
    prompt = PROMPT_INTERPRET.format(transcript=transcript)
    try:
        result = get_llm().invoke([HumanMessage(content=prompt)]).content.strip()
        result = re.sub(r"^```(?:json)?|```$", "", result, flags=re.IGNORECASE).strip()
        parsed = json.loads(result)
        return parsed if isinstance(parsed, dict) else {}
    except Exception as exc:
        logger.warning(
            "Interpretação inicial indisponível; usando roteador local: %s", exc
        )
        return {}


def extract_intent_node(state: AgentState):
    """Classifica a mensagem e prioriza dados determinísticos de agendamento."""
    """Nó 1: Classifica a intenção do usuário (Zero-Cost Router NLP/LLM)."""
    messages = state["messages"]
    last_msg_content = messages[-1].content
    if not isinstance(last_msg_content, str):
        last_msg_content = str(last_msg_content)
    last_msg = last_msg_content.strip().lower()

    # O router local resolve intenções claras e só deixa mensagens ambíguas para a LLM.
    routing = route_message(messages[-1].content, messages)
    human_turns = sum(
        1 for message in messages if getattr(message, "type", None) == "human"
    )
    if human_turns <= 2 and routing["intent"] not in {
        "OFF_TOPIC",
        "URGENCIA",
        "FRUSTRACAO_HANDOFF",
    }:
        interpretation = _interpret_initial_messages(messages)
        semantic_intent = interpretation.get("intent")
        semantic_intent = semantic_intent if semantic_intent in {"AGENDAMENTO"} else None
        semantic_complaint = interpretation.get("complaint_detected")
        if not isinstance(semantic_complaint, bool):
            semantic_complaint = None
        routing = route_message(
            messages[-1].content,
            messages,
            semantic_complaint=semantic_complaint,
            semantic_intent=semantic_intent,
        )
        if isinstance(interpretation.get("third_party"), bool):
            routing["entities"]["third_party"] = (
                routing["entities"]["third_party"] or interpretation["third_party"]
            )
        routing["semantic_interpretation"] = {
            "intent": interpretation.get("intent"),
            "complaint_detected": interpretation.get("complaint_detected"),
        }
    ai_mode = load_config().get("ai_mode", "balanced")
    confidence_threshold = {
        "economic": 0.90,
        "balanced": 0.90,
        "intelligent": 0.99,
    }.get(ai_mode, 0.90)
    previous_booking = state.get("booking")
    protected_intents = {
        "OFF_TOPIC",
        "URGENCIA",
        "FRUSTRACAO_HANDOFF",
        "LOCATION_REQUEST",
        "CANCELAMENTO",
        "REAGENDAMENTO",
    }
    if (
        booking_is_active(previous_booking)
        and routing.get("intent") not in protected_intents
    ):
        routing["intent"] = "AGENDAMENTO"
        routing["confidence"] = max(float(routing.get("confidence", 0)), 0.99)

    booking = update_booking_state(
        previous_booking,
        messages[-1].content,
        messages,
        routing,
    )

    # Sync with persistent patient_profile
    profile = state.get("patient_profile", {})
    if profile:
        if profile.get("cpf"):
            booking["cpf"] = profile["cpf"]
        if profile.get("patient_name"):
            booking["patient_name"] = profile["patient_name"]
        if profile.get("birth_date"):
            booking["birth_date"] = profile["birth_date"]
        if profile.get("email"):
            booking["email"] = profile["email"]
        if profile.get("payment_type"):
            booking["payment_type"] = profile["payment_type"]
        if profile.get("insurance_card"):
            booking["insurance_card"] = profile["insurance_card"]
        if profile.get("symptoms"):
            booking["complaint_collected"] = True
        if profile.get("symptoms_duration"):
            booking["duration_collected"] = True
        if profile.get("medications"):
            booking["medication_collected"] = True

    from app.core.booking_state import _derive_stage

    booking["stage"] = _derive_stage(booking)

    record_validation = (
        validate_booking_state(booking) if routing.get("intent") == "AGENDAMENTO" else {}
    )
    if record_validation:
        routing["record_validation"] = record_validation
        routing["next_action"] = booking_next_action(booking)

    if routing["confidence"] >= confidence_threshold:
        logger.info(
            "Roteamento determinístico: intenção=%s confiança=%s estágio=%s próxima_ação=%s terceiro=%s",
            routing["intent"],
            routing["confidence"],
            booking.get("stage"),
            routing["next_action"],
            routing["entities"]["third_party"],
        )
        return {
            "intent": routing["intent"],
            "routing": routing,
            "record_validation": record_validation,
            "booking": booking,
        }

    # CPF is a deterministic scheduling signal; preserve leading zeros outside the LLM.
    if extract_cpf_from_text(last_msg):
        logger.info("CPF válido recebido; avançando para coleta da data de nascimento")
        booking = update_booking_state(
            state.get("booking"), messages[-1].content, messages, routing
        )
        profile = state.get("patient_profile", {})
        if profile:
            if profile.get("cpf"):
                booking["cpf"] = profile["cpf"]
            if profile.get("patient_name"):
                booking["patient_name"] = profile["patient_name"]
            if profile.get("birth_date"):
                booking["birth_date"] = profile["birth_date"]
            if profile.get("email"):
                booking["email"] = profile["email"]
            if profile.get("payment_type"):
                booking["payment_type"] = profile["payment_type"]
            if profile.get("insurance_card"):
                booking["insurance_card"] = profile["insurance_card"]
        from app.core.booking_state import _derive_stage

        booking["stage"] = _derive_stage(booking)
        record_validation = validate_booking_state(booking)
        routing["record_validation"] = record_validation
        routing["next_action"] = booking_next_action(booking)
        return {
            "intent": "AGENDAMENTO",
            "routing": routing,
            "record_validation": record_validation,
            "booking": booking,
        }



    # 2. Fallback: Se for ambíguo, invocamos LLM (gpt-4o-mini)
    logger.info("Intenção ambígua. Invocando LLM Fallback (Zero-Cost Router)...")
    prompt = PROMPT_FALLBACK.format(last_msg=last_msg)

    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()

    if "URGENCIA" in response:
        intent = "URGENCIA"
    elif "REAGENDAMENTO" in response:
        intent = "REAGENDAMENTO"
    elif "CANCELAMENTO" in response:
        intent = "CANCELAMENTO"
    elif "CONFIRMACAO" in response:
        intent = "CONFIRMACAO"
    elif "AGENDAMENTO" in response or "AGENDAR" in response:
        intent = "AGENDAMENTO"
    else:
        intent = "DUVIDA"

    logger.info(f"Intenção identificada via LLM: {intent}")
    routing["intent"] = intent
    booking = update_booking_state(
        state.get("booking"), messages[-1].content, messages, routing
    )
    profile = state.get("patient_profile", {})
    if profile:
        if profile.get("cpf"):
            booking["cpf"] = profile["cpf"]
        if profile.get("patient_name"):
            booking["patient_name"] = profile["patient_name"]
        if profile.get("birth_date"):
            booking["birth_date"] = profile["birth_date"]
        if profile.get("email"):
            booking["email"] = profile["email"]
        if profile.get("payment_type"):
            booking["payment_type"] = profile["payment_type"]
        if profile.get("insurance_card"):
            booking["insurance_card"] = profile["insurance_card"]
    from app.core.booking_state import _derive_stage

    booking["stage"] = _derive_stage(booking)
    record_validation = validate_booking_state(booking) if intent == "AGENDAMENTO" else {}
    if record_validation:
        routing["record_validation"] = record_validation
        routing["next_action"] = booking_next_action(booking)
    return {
        "intent": intent,
        "routing": routing,
        "record_validation": record_validation,
        "booking": booking,
    }


def route_intent(
    state: AgentState,
) -> Literal[
    "fetch_context",
    "clinical_triage",
    "urgency_flow",
    "handoff_flow",
    "cancellation_flow",
    "rescheduling_flow",
    "off_topic_flow",
    "location_flow",
]:
    """Direciona o estado para o fluxo especializado correspondente."""
    intent = state.get("intent")
    if intent == "FRUSTRACAO_HANDOFF":
        return "handoff_flow"
    if intent == "URGENCIA":
        return "urgency_flow"
    if intent == "OFF_TOPIC":
        return "off_topic_flow"
    if intent == "LOCATION_REQUEST":
        return "location_flow"
    if intent == "CANCELAMENTO":
        return "cancellation_flow"
    if intent == "REAGENDAMENTO":
        return "rescheduling_flow"
    if intent == "AGENDAMENTO":
        return "clinical_triage"
    return "fetch_context"


async def cancellation_flow_node(state: AgentState):
    """Nó dedicado ao fluxo de cancelamento."""
    msg = MSG_CANCELLATION
    return {"context": msg}


async def rescheduling_flow_node(state: AgentState):
    """Nó dedicado ao fluxo de reagendamento."""
    msg = MSG_RESCHEDULING
    return {"context": msg}


def handoff_flow_node(state: AgentState):
    """Produz a resposta de transferência para a equipe humana."""
    msg = MSG_HANDOFF
    return {"messages": [AIMessage(content=msg)]}


def urgency_flow_node(state: AgentState):
    """Interrompe o fluxo normal e orienta o paciente em urgência."""
    msg = MSG_URGENCY
    return {"messages": [AIMessage(content=msg)]}


async def extract_memory_node(state: AgentState):
    """Nó: Extrai memória de forma contínua em background."""
    from app.core.patient_data import extract_patient_profile

    messages = state.get("messages", [])
    current_profile = state.get("patient_profile") or {}

    if messages and getattr(messages[-1], "type", "") == "human":
        # extract_patient_profile was made async? No, it uses llm.invoke which is sync.
        # But wait, ChatOpenAI invoke works in async environment if wrapped or just executed. It's safe.
        # Or we can just use run_in_executor if needed, but it should be fine here for now.
        new_profile = extract_patient_profile(messages, current_profile)
        return {"patient_profile": new_profile}
    return {}


def location_flow_node(state: AgentState):
    """Entrega a localização após confirmação, sem reabrir o cadastro."""
    return {
        "messages": [
            AIMessage(
                content=(
                    f"Claro. Endereço da Clínica Lifeline One:\n{clinic_location_text()}"
                )
            )
        ]
    }


async def off_topic_flow_node(state: AgentState):
    """Lida com mensagens fora do escopo médico/atendimento da clínica."""
    return {"messages": [AIMessage(content=MSG_OFF_TOPIC)]}


async def generate_response_node(state: AgentState):
    """Monta o prompt final e solicita resposta com as ferramentas permitidas."""
    """Nó 3: Gera a resposta da Amanda com base no contexto, intenção, perfil do paciente e histórico seguro."""
    intent = state.get("intent", "duvidas_clinica")
    context = state.get("context", "")
    messages = state["messages"]
    routing = state.get("routing", {})
    booking = state.get("booking", {})

    if context.startswith("[CACHED_PUBLIC_RESPONSE]\n"):
        return {"messages": [AIMessage(content=context.split("\n", 1)[1])]}

    action_instruction = ""
    next_action = routing.get("next_action")

    if intent == "AGENDAMENTO" and routing.get("next_action") == "COLLECT_COMPLAINT":
        if not booking.get("complaint_collected"):
            action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: O paciente quer agendar uma consulta. Pergunte de forma empática e natural o motivo da consulta ou os sintomas que ele está sentindo. Se o paciente não quiser responder ou fugir do assunto, não insista e prossiga."
        elif not booking.get("duration_collected"):
            action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: O paciente já informou a queixa. Seja empática e pergunte há quanto tempo ele está com esses sintomas. Se o paciente ignorar essa pergunta repetidas vezes, não insista, aceite a resposta dada e siga adiante."
        elif not booking.get("medication_collected"):
            action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: Entenda o problema do paciente com empatia e pergunte se ele tem tomado algum medicamento para aliviar os sintomas ultimamente. Se o paciente ignorar ou fugir da pergunta, assuma que não tomou nada e pare de perguntar."

    if intent == "AGENDAMENTO" and next_action == "AWAIT_SLOT":
        action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: Informe ao paciente que você não encontrou a escolha dele entre os horários apresentados e peça para ele informar o dia e o horário desejados."
    if next_action == "REVIEW_PATIENT_DATA":
        action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: Existe uma divergência nos dados. Peça educadamente para o paciente confirmar o nome completo, CPF e data de nascimento por segurança."

    if (
        intent == "AGENDAMENTO"
        and next_action == "CHECK_AVAILABILITY"
        and "[APENAS_APRESENTAR_HORARIOS]" in context
    ):
        result_match = re.search(
            r"\[AGENDA_RESULTADO\]\s*(.*?)\s*\[FIM_AGENDA_RESULTADO\]", context, re.DOTALL
        )
        agenda_result = result_match.group(1).strip() if result_match else ""
        if agenda_result and "erro" not in agenda_result.lower():
            action_instruction = f"[INSTRUÇÃO OBRIGATÓRIA]: Apresente os seguintes horários disponíveis e pergunte qual ele prefere:\n{agenda_result}"
        else:
            action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: Informe que você não conseguiu consultar os horários no momento e sugira tentar novamente em instantes."

    if intent == "LOCATION_REQUEST":
        from app.core.clinic_location import clinic_location_text

        action_instruction = f"[INSTRUÇÃO OBRIGATÓRIA]: Envie o endereço da Clínica Lifeline One:\n{clinic_location_text()}\nApós o envio, conclua o atendimento cordialmente e não inicie novas perguntas."

    if intent == "AGENDAMENTO" and next_action == "CONFIRM_SLOT":
        result_match = re.search(
            r"Resultado interno da criacao:\s*(.*)", context, re.DOTALL
        )
        result = result_match.group(1) if result_match else ""
        if any(
            term in result.lower() for term in ("confirmado", "registrado", "sucesso")
        ):
            slot = booking.get("selected_slot") or {}
            date_parts = slot.get("date", "").split("-")
            formatted_date = (
                "/".join(reversed(date_parts))
                if len(date_parts) == 3
                else slot.get("date", "")
            )
            link_match = re.search(r"https?://\S+", result)
            link = link_match.group(0).rstrip(".,") if link_match else ""
            link_text = f" O link para adicionar na agenda é: {link}" if link else ""
            first_name = (booking.get("patient_name") or "Paciente").split()[0]
            action_instruction = f"[INSTRUÇÃO OBRIGATÓRIA]: Confirme com entusiasmo que a consulta de {first_name} está marcada para {formatted_date} às {slot.get('time')}.{link_text} Em seguida, pergunte se ele deseja receber a localização da clínica."
        else:
            action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: Informe com educação que não foi possível concluir o agendamento nesse horário e que você vai verificar a disponibilidade novamente."

    if intent == "AGENDAMENTO" and next_action in {
        "COLLECT_NAME",
        "COLLECT_CPF",
        "COLLECT_BIRTH_DATE",
        "COLLECT_EMAIL",
        "COLLECT_PAYMENT_TYPE",
        "COLLECT_INSURANCE_CARD",
    }:
        third_party = booking.get("patient_type") == "third_party"
        if next_action == "COLLECT_NAME":
            action_instruction = (
                "[INSTRUÇÃO OBRIGATÓRIA]: Solicite o nome completo da pessoa que será consultada."
                if third_party
                else "[INSTRUÇÃO OBRIGATÓRIA]: Solicite o nome completo do próprio paciente."
            )
        elif next_action == "COLLECT_CPF":
            action_instruction = (
                "[INSTRUÇÃO OBRIGATÓRIA]: Peça o CPF da pessoa que será consultada."
                if third_party
                else "[INSTRUÇÃO OBRIGATÓRIA]: Peça o CPF do paciente."
            )
        elif next_action == "COLLECT_BIRTH_DATE":
            action_instruction = (
                "[INSTRUÇÃO OBRIGATÓRIA]: Peça a data de nascimento do paciente."
            )
        elif next_action == "COLLECT_EMAIL":
            action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: Peça um endereço de e-mail do paciente (informe que é para envio de documentos e recibos)."
        elif next_action == "COLLECT_PAYMENT_TYPE":
            action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: Pergunte se o atendimento será particular ou por convênio."
        elif next_action == "COLLECT_INSURANCE_CARD":
            action_instruction = "[INSTRUÇÃO OBRIGATÓRIA]: Peça o número da carteirinha do convênio (ou uma foto dela)."

    patient_profile_str = ""
    if booking.get("patient_type") == "third_party":
        patient_profile_str += (
            "ATENDIMENTO PARA TERCEIRO: o contato atual é o responsável pelo paciente. "
            "Colete e use o nome, CPF e data de nascimento da pessoa que será consultada. "
            "Não use automaticamente o nome do responsável como nome do paciente. "
            "Mantenha o telefone do responsável para contato.\n\n"
        )

    # [CONSCIÊNCIA TEMPORAL E CALENDÁRIO ABSOLUTO]
    now_sp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    dias_semana = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo",
    ]
    dia_str = dias_semana[now_sp.weekday()]
    data_str = now_sp.strftime("%d/%m/%Y")
    hora_str = now_sp.strftime("%H:%M")
    relogio_anchor = f"\n[RELÓGIO DO SISTEMA]\nHoje é {dia_str}, {data_str}. A hora atual é {hora_str}. Use esta data como referencial para interpretar amanhã e próxima semana.\n"

    # [ESTADO DO PACIENTE: PRIMEIRO CONTATO VS RECORRENTE]
    contact_status_str = ""
    latest_cpf = extract_latest_cpf(messages)
    if latest_cpf:
        patient_profile_str = (
            "DADO CONFIRMADO PELO PACIENTE: CPF válido recebido nesta conversa "
            f"({latest_cpf}). Não peça o nome novamente; prossiga solicitando apenas a data de nascimento.\n\n"
        )
    thread_id = state.get("thread_id", "")
    try:
        async with AsyncSessionLocal() as session:
            active_contact = None
            if thread_id:
                clean_phone = re.sub(r"\D", "", thread_id)
                stmt = select(Contact).where(
                    Contact.phone_number.contains(
                        clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone
                    )
                )
                res = await session.execute(stmt)
                active_contact = res.scalars().first()

            # Checa se é o início absoluto da conversa
            msg_count = len(messages) if messages else 0
            # Note: na primeira mensagem o array messages contém apenas 1 item
            is_initial_turn = msg_count <= 1

            if active_contact:
                profile_parts = []
                patient_name = active_contact.name
                if patient_name:
                    profile_parts.append(f"Nome do Paciente: {patient_name}")
                if active_contact.phone_number:
                    profile_parts.append(
                        f"Telefone/WhatsApp: {active_contact.phone_number}"
                    )
                if active_contact.insurance_operator:
                    profile_parts.append(
                        f"Convênio: {active_contact.insurance_operator} (Plano: {active_contact.insurance_plan_name or 'Padrão'})"
                    )
                if active_contact.insurance_card_number:
                    profile_parts.append(
                        f"Matrícula do Plano: {active_contact.insurance_card_number}"
                    )
                if active_contact.stage == "agendado":
                    profile_parts.append(
                        "Status: Já possui agendamento prévio ou histórico na clínica."
                    )

                if profile_parts and not is_initial_turn:
                    patient_profile_str = (
                        "FICHA DO PACIENTE (DADOS CADASTRAIS):\n"
                        + "\n".join(profile_parts)
                        + "\n\n"
                    )

                # O primeiro turno sempre apresenta a assistente e a clínica.
                # O nome recebido do WhatsApp não comprova histórico de atendimento.
                if is_initial_turn:
                    name_hint = (
                        f" Pode chamar o paciente pelo primeiro nome ({patient_name}), se isso soar natural."
                        if patient_name
                        else ""
                    )
                    contact_status_str = (
                        "TIPO DE ATENDIMENTO: PRIMEIRO TURNO DESTA CONVERSA / BOAS-VINDAS\n"
                        "APRESENTAÇÃO OBRIGATÓRIA: Apresente-se como Amanda e cite a Clínica Lifeline One."
                        f"{name_hint} Não diga que o paciente é recorrente apenas por existir um nome cadastrado.\n\n"
                    )
            else:
                if is_initial_turn:
                    contact_status_str = (
                        "TIPO DE ATENDIMENTO: PRIMEIRO TURNO DESTA CONVERSA / BOAS-VINDAS\n"
                        "APRESENTAÇÃO OBRIGATÓRIA: Apresente-se como Amanda e cite a Clínica Lifeline One.\n\n"
                    )
    except Exception as err:
        logger.debug(f"Aviso memória de longo prazo: {err}")

    # [MEMÓRIA INTELIGENTE: DADOS EXTRAÍDOS CONTINUAMENTE]
    patient_profile = state.get("patient_profile", {})
    if patient_profile:
        patient_profile_str += "\n[MEMÓRIA DA CONVERSA - DADOS DO PACIENTE]\n"
        for k, v in patient_profile.items():
            if v:
                patient_profile_str += f"- {k}: {v}\n"
        patient_profile_str += "\n"

    # [CONSCIÊNCIA TEMPORAL DINÂMICA & CALENDÁRIO CANÔNICO ANTI-ALUCINAÇÃO]
    now_sp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    hora = now_sp.hour
    weekdays_pt = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo",
    ]
    dia_semana_hoje = weekdays_pt[now_sp.weekday()]

    if 6 <= hora < 12:
        saudacao_turno = "MANHÃ (Use 'Bom dia' se for iniciar contato)"
    elif 12 <= hora < 18:
        saudacao_turno = "TARDE (Use 'Boa tarde' se for iniciar contato)"
    else:
        saudacao_turno = "NOITE/MADRUGADA (Use 'Boa noite' se for iniciar contato. Acolha informando que mesmo fora do expediente da recepção, você está à disposição para adiantar o agendamento)"

    # Constrói o mapa cronológico exato dos próximos 7 dias para a IA nunca errar o dia da semana
    calendario_linhas = [
        f"• HOJE: {dia_semana_hoje}, {now_sp.strftime('%d/%m/%Y')} (ISO: {now_sp.strftime('%Y-%m-%d')})"
    ]
    for i in range(1, 8):
        d_futuro = now_sp + datetime.timedelta(days=i)
        dia_sem = weekdays_pt[d_futuro.weekday()]
        calendario_linhas.append(
            f"• Próximo dia (+{i}): {dia_sem}, {d_futuro.strftime('%d/%m/%Y')} (Use '{d_futuro.strftime('%Y-%m-%d')}' nas tools)"
        )

    calendario_tabela = "\n".join(calendario_linhas)

    temporal_anchor = (
        f"CALENDÁRIO OFICIAL DA CLÍNICA (RIGOR CRONOLÓGICO ABSOLUTO):\n"
        f"{calendario_tabela}\n"
        f"TURNO ATUAL: {saudacao_turno}\n"
        f"REGRA DE AGENDAMENTO: Ao citar qualquer dia da semana (ex: próxima segunda-feira, amanhã, etc.), consulte OBRIGATORIAMENTE a tabela acima para informar a data correta. NUNCA invente ou calcule de cabeça.\n\n"
    )

    enriched_context = (
        temporal_anchor
        + (contact_status_str if contact_status_str else "")
        + (patient_profile_str if patient_profile_str else "")
        + context
    )
    if action_instruction:
        enriched_context += f"\n\n{action_instruction}"

    # Busca a última mensagem do usuário para heurísticas do Builder
    user_msg_text = ""
    for m in reversed(messages):
        if m.type == "human":
            user_msg_text = m.content
            break

    system_prompt = PersonaBuilder.build_dynamic_prompt(
        intent=intent,
        rag_context=enriched_context,
        chat_history="O LangGraph gerencia este histórico de forma persistente.",
        user_message=f"[Mensagem atual do paciente:]\n{user_msg_text}",
    )
    # Filtra mensagens problemáticas (órfãs, dicts, RemoveMessage) para evitar erro 400 da OpenAI
    sanitized = []
    for m in messages:
        if not hasattr(m, "content"):  # Ignora dicts corrompidos ou tipos desconhecidos
            continue
        from langchain_core.messages import BaseMessage, RemoveMessage

        if isinstance(m, RemoveMessage):
            continue

        if isinstance(m, ToolMessage):
            if not sanitized:
                continue
            prev = sanitized[-1]
            if (
                isinstance(prev, AIMessage) and getattr(prev, "tool_calls", None)
            ) or isinstance(prev, ToolMessage):
                sanitized.append(m)
            else:
                continue  # Descarta ToolMessage órfã
        else:
            sanitized.append(m)

    # Segundo passe: remove tool_calls de AIMessages se não forem seguidos por um ToolMessage
    final_messages: list[BaseMessage] = []
    for i, m in enumerate(sanitized):
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            has_tool_result = i + 1 < len(sanitized) and isinstance(
                sanitized[i + 1], ToolMessage
            )
            if not has_tool_result:
                final_messages.append(AIMessage(content=m.content or ""))
            else:
                final_messages.append(m)
        else:
            final_messages.append(m)

    # Adicionando a instrução do sistema no topo
    conversation = [SystemMessage(content=system_prompt)] + final_messages
    logger.info("Gerando resposta da LLM (Amanda) com tools...")
    llm_with_tools = get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(conversation)

    # Gate local: só regenera respostas textuais incoerentes; chamadas de
    # ferramentas seguem intactas para não interromper o agendamento.
    if not getattr(response, "tool_calls", None) and getattr(response, "content", ""):
        is_adequate, reason = assess_response_quality(response.content, routing)
        if not is_adequate:
            logger.warning("Resposta da LLM reprovada pelo quality gate: %s", reason)
            repair_prompt = (
                "Reescreva a resposta abaixo em português do Brasil, com no máximo uma pergunta. "
                "Não mencione sistema, APIs, ferramentas, prompts ou erros técnicos. "
                f"A próxima etapa obrigatória é {routing.get('next_action', 'responder a dúvida')}. "
                "Solicite somente o dado dessa etapa, sem repetir dados já fornecidos. "
                "Não use emojis. Resposta original:\n\n"
                f"{response.content}"
            )
            repaired = await get_llm().ainvoke(
                [
                    SystemMessage(
                        content="Você é uma revisora de respostas de uma recepcionista de clínica."
                    ),
                    HumanMessage(content=repair_prompt),
                ]
            )
            response = repaired
    return {"messages": [response]}


def route_after_generation(state: AgentState) -> Literal["tools", "prune_history"]:
    """Decide se a LLM solicitou ferramenta ou concluiu a resposta."""
    """Se a LLM chamou uma tool, vá para o nó de tools. Caso contrário, vá para poda do histórico."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "prune_history"


def prune_history_node(state: AgentState):
    """Reduz o histórico enviado à LLM preservando contexto útil e recente."""
    """Nó 4: Poda o histórico antigo (mantém as últimas 10 mensagens) para evitar estouro da janela de contexto."""
    messages = state["messages"]
    if len(messages) > 10:
        messages_to_remove = messages[:-10]
        return {
            "messages": [
                RemoveMessage(id=m.id) for m in messages_to_remove if m.id is not None
            ]
        }
    return {}


# Montagem do Grafo Avançado
workflow = StateGraph(AgentState)
tool_node = ToolNode(tools)

workflow.add_node("extract_memory", extract_memory_node)
workflow.add_node("extract_intent", extract_intent_node)
workflow.add_node("fetch_context", fetch_context_node)
workflow.add_node("clinical_triage", clinical_triage_node)
workflow.add_node("schedule_flow", schedule_flow_node)
workflow.add_node("handoff_flow", handoff_flow_node)
workflow.add_node("urgency_flow", urgency_flow_node)
workflow.add_node("off_topic_flow", off_topic_flow_node)
workflow.add_node("location_flow", location_flow_node)
workflow.add_node("cancellation_flow", cancellation_flow_node)
workflow.add_node("rescheduling_flow", rescheduling_flow_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_node("tools", tool_node)
workflow.add_node("prune_history", prune_history_node)

workflow.add_edge(START, "extract_memory")
workflow.add_edge("extract_memory", "extract_intent")
workflow.add_conditional_edges("extract_intent", route_intent)
workflow.add_edge("fetch_context", "generate_response")
workflow.add_edge("clinical_triage", "schedule_flow")
workflow.add_edge("schedule_flow", "generate_response")
workflow.add_edge("handoff_flow", "prune_history")
workflow.add_edge("urgency_flow", "prune_history")
workflow.add_edge("off_topic_flow", "prune_history")
workflow.add_edge("location_flow", "prune_history")
workflow.add_edge("cancellation_flow", "generate_response")
workflow.add_edge("rescheduling_flow", "generate_response")

workflow.add_conditional_edges("generate_response", route_after_generation)
workflow.add_edge("tools", "generate_response")
workflow.add_edge("prune_history", END)

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings

# Database URL for checkpointer
db_url = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ia_amanda"
)
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

# Configura o Checkpointer do Postgres (Será inicializado na primeira chamada)
_checkpointer = None
app_graph = None


async def init_checkpointer():
    """Inicializa o checkpoint persistente que mantém continuidade das conversas."""
    global _checkpointer, app_graph
    if _checkpointer is None:
        import psycopg
        from psycopg_pool import AsyncConnectionPool

        async with await psycopg.AsyncConnection.connect(db_url, autocommit=True) as conn:
            temp_saver = AsyncPostgresSaver(conn)
            await temp_saver.setup()

        pool = AsyncConnectionPool(db_url, max_size=10, open=False)
        await pool.open()

        _checkpointer = AsyncPostgresSaver(pool)
        app_graph = workflow.compile(checkpointer=_checkpointer)


async def process_user_message(thread_id: str, message: str) -> str:
    """Executa o grafo completo para uma mensagem e retorna o texto final."""
    # Garante que o checkpointer e o grafo estão inicializados
    if app_graph is None:
        await init_checkpointer()

    # [CAMADA 1: INPUT SHIELD] Interceptação de ataques adversariais / jailbreak

    if await detect_adversarial_attempt(message):
        logger.warning(
            f"[SECURITY SHIELD] Prompt injection interceptado para thread {thread_id}"
        )
        return "Olá! Sou a Amanda, assistente da clínica. Como posso ajudar com suas dúvidas ou agendamento de consultas?"

    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    # [OBSERVABILIDADE] Adiciona Langfuse Callback Handler se configurado via ENV
    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        try:
            from langfuse.langchain import CallbackHandler

            langfuse_handler = CallbackHandler(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
                session_id=thread_id,
            )
            config["callbacks"] = [langfuse_handler]
        except Exception as e:
            logger.warning(f"Não foi possível inicializar Langfuse: {e}")

    # Envelopa o input com delimitadores seguros para proteger o modelo contra quebras de contexto
    wrapped_message = sanitize_and_wrap_user_input(message)
    input_state = {
        "messages": [HumanMessage(content=wrapped_message)],
        "thread_id": thread_id,
    }

    logger.info(f"LangGraph processando thread {thread_id} com AsyncPostgresSaver.")

    assert app_graph is not None
    
    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        try:
            from langfuse import propagate_attributes
            with propagate_attributes(
                trace_name="IA Amanda Orchestrator",
                session_id=thread_id,
                user_id=thread_id,
                tags=["amanda-bot", "langgraph", "production"],
            ):
                final_state = await app_graph.ainvoke(input_state, config=config)
        except Exception as e:
            logger.warning(f"Aviso Langfuse propagate_attributes falhou: {e}")
            final_state = await app_graph.ainvoke(input_state, config=config)
    else:
        final_state = await app_graph.ainvoke(input_state, config=config)

    ai_content = final_state["messages"][-1].content

    return ai_content
