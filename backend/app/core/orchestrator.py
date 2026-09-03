"""Orquestração do atendimento: intenção, contexto, ferramentas e resposta."""

import os
import logging
import datetime
import re
from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, RemoveMessage
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, RemoveMessage, AIMessage
from langchain_openai import ChatOpenAI
from app.core.rag import retrieve_context
from app.core.prompt_master import PersonaBuilder
from app.core.patient_data import contains_date, extract_cpf_from_text, extract_latest_cpf, extract_latest_date, extract_payment_type, has_patient_complaint
from app.core.conversation_router import route_message

from langgraph.checkpoint.memory import MemorySaver
import operator
from app.services.google_calendar import check_availability, create_event, cancel_event, reschedule_event, confirm_event
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)

# Checkpointer global para manter a memória enquanto o servidor estiver rodando
memory = MemorySaver()

from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """Estado serializável compartilhado pelos nós do grafo."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: str
    intent: str
    thread_id: str
    routing: dict

from app.api.endpoints.settings import load_config

def get_llm():
    """Inicializa a LLM com a configuração persistida da aplicação."""
    cfg = load_config()
    model_name = cfg.get("model", "gpt-4o-mini")
    temp = float(cfg.get("temperature", 0.2))
    return ChatOpenAI(model=model_name, temperature=temp)

tools = [check_availability, create_event, cancel_event, reschedule_event, confirm_event]

def extract_intent_node(state: AgentState):
    """Classifica a mensagem e prioriza dados determinísticos de agendamento."""
    """Nó 1: Classifica a intenção do usuário (Zero-Cost Router NLP/LLM)."""
    messages = state['messages']
    last_msg = messages[-1].content.strip().lower()

    # O router local resolve intenções claras e só deixa mensagens ambíguas para a LLM.
    routing = route_message(messages[-1].content, messages)
    ai_mode = load_config().get("ai_mode", "balanced")
    confidence_threshold = {
        "economic": 0.90,
        "balanced": 0.90,
        "intelligent": 0.99,
    }.get(ai_mode, 0.90)
    if routing["confidence"] >= confidence_threshold:
        logger.info(
            "Roteamento determinístico: intenção=%s confiança=%s próxima_ação=%s terceiro=%s",
            routing["intent"],
            routing["confidence"],
            routing["next_action"],
            routing["entities"]["third_party"],
        )
        return {"intent": routing["intent"], "routing": routing}

    # CPF is a deterministic scheduling signal; preserve leading zeros outside the LLM.
    if extract_cpf_from_text(last_msg):
        logger.info("CPF válido recebido; avançando para coleta da data de nascimento")
        return {"intent": "AGENDAMENTO"}
    
    # 1. Heurística Local Rápida (Zero-Cost NLP)
    import re
    if any(k in last_msg for k in ["humano", "atendente", "falar com pessoa", "tá difícil", "não entende", "péssimo", "horrível", "burra", "burro", "robo"]):
        logger.info("Intenção identificada via Heurística: FRUSTRACAO_HANDOFF")
        return {"intent": "FRUSTRACAO_HANDOFF"}

    if any(k in last_msg for k in ["urgência", "urgencia", "emergência", "emergencia", "falta de ar", "sufocando", "glote", "anafilaxia", "grave", "pronto socorro"]):
        logger.info("Intenção identificada via Heurística: URGENCIA")
        return {"intent": "URGENCIA"}
        
    if any(k in last_msg for k in ["remarcar", "reagendar", "mudar o dia", "mudar a hora", "mudar horario", "mudar a data"]):
        logger.info("Intenção identificada via Heurística: REAGENDAMENTO")
        return {"intent": "REAGENDAMENTO"}

    if any(k in last_msg for k in ["cancelar", "desmarcar"]):
        logger.info("Intenção identificada via Heurística: CANCELAMENTO")
        return {"intent": "CANCELAMENTO"}

    if any(k in last_msg for k in ["agendar", "marcar", "consulta", "horário", "horario", "vaga", "quero ir"]):
        logger.info("Intenção identificada via Heurística: AGENDAMENTO")
        return {"intent": "AGENDAMENTO"}
        
    # 2. Fallback: Se for ambíguo, invocamos LLM (gpt-4o-mini)
    logger.info("Intenção ambígua. Invocando LLM Fallback (Zero-Cost Router)...")
    prompt = f"""Analise a mensagem do paciente e classifique a intenção principal em UMA das palavras abaixo:
- URGENCIA (falta de ar, emergência)
- AGENDAMENTO (marcar consulta, interesse em agendar)
- REAGENDAMENTO (remarcar, trocar de dia)
- CANCELAMENTO (desmarcar)
- CONFIRMACAO (confirmar que vai na consulta, aceitar o horário)
- DUVIDA (dúvidas em geral, perguntas sobre clínica, oi/bom dia)

Mensagem: "{last_msg}"
Classificação:"""
    
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
    return {"intent": intent, "routing": routing}

def route_intent(state: AgentState) -> Literal["fetch_context", "schedule_flow", "urgency_flow", "handoff_flow"]:
    """Direciona o estado para o fluxo especializado correspondente."""
    """Função de roteamento condicional baseada na intenção."""
    intent = state.get("intent")
    if intent == "FRUSTRACAO_HANDOFF":
        return "handoff_flow"
    if intent == "URGENCIA":
        return "urgency_flow"
    if intent == "OFF_TOPIC":
        return "off_topic_flow"
    if intent in ["AGENDAMENTO", "REAGENDAMENTO", "CANCELAMENTO"]:
        return "schedule_flow"
    return "fetch_context"

def handoff_flow_node(state: AgentState):
    """Produz a resposta de transferência para a equipe humana."""
    """Nó de Transbordo Humano."""
    msg = (
        "Compreendo perfeitamente. Estou transferindo o seu atendimento agora mesmo para a nossa equipe humana. "
        "Um de nossos recepcionistas já foi notificado e vai dar continuidade ao seu atendimento por aqui em instantes. [TRANSFERIR_HUMANO]"
    )
    return {"messages": [AIMessage(content=msg)]}

def urgency_flow_node(state: AgentState):
    """Interrompe o fluxo normal e orienta o paciente em urgência."""
    """Nó de Alerta/Urgência: Gera mensagem de acolhimento emergencial e orienta buscar pronto-socorro."""
    msg = (
        "⚠️ Identifiquei que você pode estar passando por uma situação de urgência ou necessitando de atenção imediata.\n\n"
        "Se estiver com sintomas agudos (como falta de ar súbita ou reação alérgica severa), por favor, *procure o Pronto Socorro mais próximo imediatamente*.\n\n"
        "Já notifiquei nossa equipe clínica prioritariamente para assumir seu atendimento por aqui."
    )
    return {"messages": [AIMessage(content=msg)]}


def off_topic_flow_node(state: AgentState):
    """Recusa assuntos externos e reconduz o contato ao atendimento clínico."""
    msg = (
        "Posso ajudar apenas com informações da Clínica Lifeline One, orientações administrativas "
        "e agendamento de consultas. Vamos continuar por aqui: você deseja informações sobre a clínica "
        "ou prefere seguir com o agendamento?"
    )
    return {"messages": [AIMessage(content=msg)]}

def fetch_context_node(state: AgentState):
    """Consulta a base de conhecimento sem alterar o histórico da conversa."""
    """Nó 2a: Busca o contexto no RAG (para Dúvidas e Corpo Clínico)."""
    last_message = state['messages'][-1].content
    context = retrieve_context(last_message)
    return {"context": context}

async def schedule_flow_node(state: AgentState):
    """Consulta disponibilidade automaticamente quando os dados permitem agendamento."""
    """Nó 2b: Fluxo dedicado para agendamento com corpo clínico e regras."""
    last_message = state['messages'][-1].content
    intent = state.get("intent", "")
    routing = state.get("routing", {})
    if intent == "AGENDAMENTO" and not has_patient_complaint(state.get("messages", [])):
        # Não consulta RAG nem agenda antes de conhecer o motivo da consulta.
        return {"context": ""}

    if intent == "AGENDAMENTO" and routing.get("next_action") == "CONFIRM_SLOT":
        entities = routing.get("entities", {})
        slot = entities.get("preferred_slot") or {}
        patient_name = entities.get("name") or ""
        cpf = entities.get("cpf") or extract_latest_cpf(state.get("messages", []))
        dob = extract_latest_date(state.get("messages", []))
        if slot.get("date") and slot.get("time") and patient_name and cpf and dob:
            booking_result = await create_event.ainvoke({
                "date_str": slot["date"],
                "time_str": slot["time"],
                "patient_name": patient_name,
                "cpf": cpf,
                "dob": dob,
                "phone": state.get("thread_id", ""),
            })
            return {
                "context": (
                    "[AGENDAMENTO_EXECUTADO]\n"
                    f"Resultado interno da criacao: {booking_result}"
                )
            }

    context = retrieve_context(f"{last_message} médicos convênios preços")
    latest_cpf = extract_latest_cpf(state.get("messages", []))
    registration_complete = latest_cpf and any(
        contains_date(getattr(message, "content", ""))
        for message in state.get("messages", [])
        if getattr(message, "type", None) == "human"
    )
    payment_type = routing.get("entities", {}).get("payment_type") or extract_payment_type(state.get("messages", []))

    if intent == "AGENDAMENTO" and registration_complete and payment_type:
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
        target_date = now.date() + datetime.timedelta(days=1)
        while target_date.weekday() == 6:
            target_date += datetime.timedelta(days=1)
        agenda_result = await check_availability.ainvoke(
            {"date_str": target_date.isoformat(), "period": "todos"}
        )
        context += (
            "\n\n[AGENDA CONSULTADA AUTOMATICAMENTE]\n"
            f"Data de referência: {target_date.isoformat()}\n"
            f"Resultado da agenda: {agenda_result}\n"
            "Apresente imediatamente as opções retornadas. Não diga que vai verificar, não aguarde confirmação e não invente horários."
        )

    return {"context": context}

async def generate_response_node(state: AgentState):
    """Monta o prompt final e solicita resposta com as ferramentas permitidas."""
    """Nó 3: Gera a resposta da Amanda com base no contexto, intenção, perfil do paciente e histórico seguro."""
    intent = state.get('intent', 'duvidas_clinica')
    context = state.get('context', '')
    messages = state['messages']
    routing = state.get("routing", {})

    # A queixa é obrigatória antes da coleta cadastral de um novo agendamento.
    # Esta trava é determinística para não depender de a LLM seguir o prompt.
    if intent == "AGENDAMENTO" and not has_patient_complaint(messages):
        return {
            "messages": [AIMessage(
                content=(
                    "Olá! Sou Amanda, recepcionista da Clínica Lifeline One. "
                    "Antes de iniciar o cadastro, preciso entender o motivo da consulta. "
                    "O que você está sentindo ou qual avaliação deseja realizar?"
                )
            )]
        }

    next_action = routing.get("next_action")
    if intent == "AGENDAMENTO" and next_action == "CONFIRM_SLOT":
        result_match = re.search(r"Resultado interno da criacao:\s*(.*)", context, re.DOTALL)
        result = result_match.group(1) if result_match else ""
        if any(term in result.lower() for term in ("confirmado", "registrado", "sucesso")):
            entities = routing.get("entities", {})
            slot = entities.get("preferred_slot") or {}
            date_parts = slot.get("date", "").split("-")
            formatted_date = "/".join(reversed(date_parts)) if len(date_parts) == 3 else slot.get("date", "")
            link_match = re.search(r"https?://\S+", result)
            link = link_match.group(0).rstrip(".,") if link_match else ""
            link_text = f"\n\nAdicione a consulta na sua agenda: {link}" if link else ""
            first_name = (entities.get("name") or "Paciente").split()[0]
            return {"messages": [AIMessage(content=(
                f"Prontinho, {first_name}. Sua consulta estÃ¡ confirmada para {formatted_date} Ã s {slot.get('time')}.{link_text}\n\n"
                "VocÃª jÃ¡ tem o endereÃ§o da clÃ­nica ou deseja que eu envie a localizaÃ§Ã£o?"
            ))]}
        return {"messages": [AIMessage(content=(
            "NÃ£o consegui concluir esse horÃ¡rio agora. Vou verificar a disponibilidade novamente para oferecer uma opÃ§Ã£o vÃ¡lida."
        ))]}
    if intent == "AGENDAMENTO" and next_action in {
        "COLLECT_NAME", "COLLECT_CPF", "COLLECT_BIRTH_DATE", "COLLECT_PAYMENT_TYPE"
    }:
        third_party = routing.get("entities", {}).get("third_party", False)
        prompts = {
            "COLLECT_NAME": (
                "Entendi. Para abrir o cadastro, informe o nome completo da pessoa que será consultada."
                if third_party else
                "Entendi. Para abrir o cadastro, informe seu nome completo, por favor."
            ),
            "COLLECT_CPF": (
                "Agora informe o CPF da pessoa que será consultada, por favor."
                if third_party else
                "Agora informe o seu CPF, por favor."
            ),
            "COLLECT_BIRTH_DATE": (
                "Para finalizar o cadastro, informe a data de nascimento da pessoa que será consultada."
                if third_party else
                "Para finalizar o cadastro, informe sua data de nascimento."
            ),
            "COLLECT_PAYMENT_TYPE": (
                "Para finalizar, você prefere atendimento particular ou utilizar um convênio?"
            ),
        }
        return {"messages": [AIMessage(content=prompts[next_action])]}

    if routing.get("entities", {}).get("third_party"):
        patient_profile_str += (
            "ATENDIMENTO PARA TERCEIRO: o contato atual é o responsável pelo paciente. "
            "Colete e use o nome, CPF e data de nascimento da pessoa que será consultada. "
            "Não use automaticamente o nome do responsável como nome do paciente. "
            "Mantenha o telefone do responsável para contato.\n\n"
        )
    
    # [CONSCIÊNCIA TEMPORAL E CALENDÁRIO ABSOLUTO]
    now_sp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_str = dias_semana[now_sp.weekday()]
    data_str = now_sp.strftime("%d/%m/%Y")
    hora_str = now_sp.strftime("%H:%M")
    relogio_anchor = f"\n[RELÓGIO DO SISTEMA]\nHoje é {dia_str}, {data_str}. A hora atual é {hora_str}. Use esta data como referencial para interpretar amanhã e próxima semana.\n"

    
    # [ESTADO DO PACIENTE: PRIMEIRO CONTATO VS RECORRENTE]
    patient_profile_str = ""
    contact_status_str = ""
    latest_cpf = extract_latest_cpf(messages)
    if latest_cpf:
        patient_profile_str = (
            "DADO CONFIRMADO PELO PACIENTE: CPF válido recebido nesta conversa "
            f"({latest_cpf}). Não peça o nome novamente; prossiga solicitando apenas a data de nascimento.\n\n"
        )
    thread_id = state.get("thread_id", "")
    try:
        from app.database import AsyncSessionLocal
        from app.models.chat import Contact
        from sqlalchemy.future import select
        import re
        
        async with AsyncSessionLocal() as session:
            active_contact = None
            if thread_id:
                clean_phone = re.sub(r"\D", "", thread_id)
                stmt = select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
                res = await session.execute(stmt)
                active_contact = res.scalars().first()
                
            # Checa se é o início absoluto da conversa
            msg_count = len(messages) if messages else 0
            # Note: na primeira mensagem o array messages contém apenas 1 item
            is_initial_turn = (msg_count <= 1)
            
            if active_contact:
                profile_parts = []
                patient_name = active_contact.name
                if patient_name:
                    profile_parts.append(f"Nome do Paciente: {patient_name}")
                if active_contact.phone_number:
                    profile_parts.append(f"Telefone/WhatsApp: {active_contact.phone_number}")
                if active_contact.insurance_operator:
                    profile_parts.append(f"Convênio: {active_contact.insurance_operator} (Plano: {active_contact.insurance_plan_name or 'Padrão'})")
                if active_contact.insurance_card_number:
                    profile_parts.append(f"Matrícula do Plano: {active_contact.insurance_card_number}")
                if active_contact.stage == "agendado":
                    profile_parts.append("Status: Já possui agendamento prévio ou histórico na clínica.")
                
                if profile_parts and not is_initial_turn:
                    patient_profile_str = "FICHA DO PACIENTE (DADOS CADASTRAIS):\n" + "\n".join(profile_parts) + "\n\n"

                # O primeiro turno sempre apresenta a assistente e a clínica.
                # O nome recebido do WhatsApp não comprova histórico de atendimento.
                if is_initial_turn:
                    name_hint = f" Pode chamar o paciente pelo primeiro nome ({patient_name}), se isso soar natural." if patient_name else ""
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

    # [CONSCIÊNCIA TEMPORAL DINÂMICA & CALENDÁRIO CANÔNICO ANTI-ALUCINAÇÃO]
    now_sp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    hora = now_sp.hour
    weekdays_pt = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    dia_semana_hoje = weekdays_pt[now_sp.weekday()]
    
    if 6 <= hora < 12:
        saudacao_turno = "MANHÃ (Use 'Bom dia' se for iniciar contato)"
    elif 12 <= hora < 18:
        saudacao_turno = "TARDE (Use 'Boa tarde' se for iniciar contato)"
    else:
        saudacao_turno = "NOITE/MADRUGADA (Use 'Boa noite' se for iniciar contato. Acolha informando que mesmo fora do expediente da recepção, você está à disposição para adiantar o agendamento)"

    # Constrói o mapa cronológico exato dos próximos 7 dias para a IA nunca errar o dia da semana
    calendario_linhas = [f"• HOJE: {dia_semana_hoje}, {now_sp.strftime('%d/%m/%Y')} (ISO: {now_sp.strftime('%Y-%m-%d')})"]
    for i in range(1, 8):
        d_futuro = now_sp + datetime.timedelta(days=i)
        dia_sem = weekdays_pt[d_futuro.weekday()]
        calendario_linhas.append(f"• Próximo dia (+{i}): {dia_sem}, {d_futuro.strftime('%d/%m/%Y')} (Use '{d_futuro.strftime('%Y-%m-%d')}' nas tools)")

    calendario_tabela = "\n".join(calendario_linhas)

    temporal_anchor = (
        f"📅 CALENDÁRIO OFICIAL DA CLÍNICA (RIGOR CRONOLÓGICO ABSOLUTO):\n"
        f"{calendario_tabela}\n"
        f"TURNO ATUAL: {saudacao_turno}\n"
        f"⚠️ REGRA DE AGENDAMENTO: Ao citar qualquer dia da semana (ex: próxima segunda-feira, amanhã, etc.), consulte OBRIGATORIAMENTE a tabela acima para informar a data correta. NUNCA invente ou calcule de cabeça.\n\n"
    )

    enriched_context = temporal_anchor + (contact_status_str if contact_status_str else "") + (patient_profile_str if patient_profile_str else "") + context

    from app.core.prompt_master import PersonaBuilder
    
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
        user_message=f"[Mensagem atual do paciente:]\n{user_msg_text}"
    )
    # Filtra mensagens problemáticas (órfãs, dicts, RemoveMessage) para evitar erro 400 da OpenAI
    sanitized = []
    for m in messages:
        if not hasattr(m, "content"): # Ignora dicts corrompidos ou tipos desconhecidos
            continue
        from langchain_core.messages import RemoveMessage, ToolMessage, BaseMessage
        if isinstance(m, RemoveMessage):
            continue
        
        if isinstance(m, ToolMessage):
            if not sanitized:
                continue
            prev = sanitized[-1]
            if isinstance(prev, AIMessage) and getattr(prev, 'tool_calls', None):
                sanitized.append(m)
            elif isinstance(prev, ToolMessage):
                sanitized.append(m)
            else:
                continue # Descarta ToolMessage órfã
        else:
            sanitized.append(m)

    # Segundo passe: remove tool_calls de AIMessages se não forem seguidos por um ToolMessage
    final_messages = []
    for i, m in enumerate(sanitized):
        if isinstance(m, AIMessage) and getattr(m, 'tool_calls', None):
            has_tool_result = (i + 1 < len(sanitized) and isinstance(sanitized[i+1], ToolMessage))
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
        from app.core.response_quality import assess_response_quality

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
            repaired = await get_llm().ainvoke([
                SystemMessage(content="Você é uma revisora de respostas de uma recepcionista de clínica."),
                HumanMessage(content=repair_prompt),
            ])
            response = repaired
    return {"messages": [response]}

def route_after_generation(state: AgentState) -> Literal["tools", "prune_history"]:
    """Decide se a LLM solicitou ferramenta ou concluiu a resposta."""
    """Se a LLM chamou uma tool, vá para o nó de tools. Caso contrário, vá para poda do histórico."""
    last_message = state['messages'][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "prune_history"

def prune_history_node(state: AgentState):
    """Reduz o histórico enviado à LLM preservando contexto útil e recente."""
    """Nó 4: Poda o histórico antigo (mantém as últimas 10 mensagens) para evitar estouro da janela de contexto."""
    messages = state['messages']
    if len(messages) > 10:
        messages_to_remove = messages[:-10]
        return {"messages": [RemoveMessage(id=m.id) for m in messages_to_remove if m.id is not None]}
    return {}

# Montagem do Grafo Avançado
workflow = StateGraph(AgentState)
tool_node = ToolNode(tools)

workflow.add_node("extract_intent", extract_intent_node)
workflow.add_node("fetch_context", fetch_context_node)
workflow.add_node("schedule_flow", schedule_flow_node)
workflow.add_node("handoff_flow", handoff_flow_node)
workflow.add_node("urgency_flow", urgency_flow_node)
workflow.add_node("off_topic_flow", off_topic_flow_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_node("tools", tool_node)
workflow.add_node("prune_history", prune_history_node)

workflow.add_edge(START, "extract_intent")
workflow.add_conditional_edges("extract_intent", route_intent)
workflow.add_edge("fetch_context", "generate_response")
workflow.add_edge("schedule_flow", "generate_response")
workflow.add_edge("handoff_flow", "prune_history")
workflow.add_edge("urgency_flow", "prune_history")
workflow.add_edge("off_topic_flow", "prune_history")

workflow.add_conditional_edges(
    "generate_response",
    route_after_generation
)
workflow.add_edge("tools", "generate_response")
workflow.add_edge("prune_history", END)

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os

# Database URL for checkpointer
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ia_amanda")
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

# Configura o Checkpointer do Postgres (Será inicializado na primeira chamada)
_checkpointer = None
app_graph = None

async def init_checkpointer():
    """Inicializa o checkpoint persistente que mantém continuidade das conversas."""
    global _checkpointer, app_graph
    if _checkpointer is None:
        from psycopg_pool import AsyncConnectionPool
        import psycopg
        
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
    from app.core.input_shield import detect_adversarial_attempt, sanitize_and_wrap_user_input
    
    if await detect_adversarial_attempt(message):
        logger.warning(f"[SECURITY SHIELD] Prompt injection interceptado para thread {thread_id}")
        return "Olá! Sou a Amanda, assistente da clínica. 🌻 Como posso te ajudar hoje com suas dúvidas ou agendamento de consultas?"
        
    config = {"configurable": {"thread_id": thread_id}}
    
    # [OBSERVABILIDADE] Adiciona Langfuse Callback Handler se configurado via ENV
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        try:
            from langfuse.callback import CallbackHandler
            langfuse_handler = CallbackHandler(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                session_id=thread_id
            )
            config["callbacks"] = [langfuse_handler]
        except Exception as e:
            logger.warning(f"Não foi possível inicializar Langfuse: {e}")

    # [CAMADA 1.5: SEMANTIC CACHING] Busca resposta ultra-rápida no Redis se já respondida
    from app.services.semantic_cache import get_cached_response
    cached_reply = await get_cached_response(message)
    if cached_reply:
        logger.info(f"[SEMANTIC CACHE] Resposta entregue instantaneamente via Cache para thread {thread_id}")
        return cached_reply

    # Envelopa o input com delimitadores seguros para proteger o modelo contra quebras de contexto
    wrapped_message = sanitize_and_wrap_user_input(message)
    input_state = {
        "messages": [HumanMessage(content=wrapped_message)],
        "thread_id": thread_id
    }
    
    logger.info(f"LangGraph processando thread {thread_id} com AsyncPostgresSaver.")
    
    final_state = await app_graph.ainvoke(input_state, config=config)
    ai_content = final_state['messages'][-1].content
    
    return ai_content
