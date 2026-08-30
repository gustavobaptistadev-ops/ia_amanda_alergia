import os
import logging
import datetime
from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, RemoveMessage
from langchain_openai import ChatOpenAI
from app.core.rag import retrieve_context
from app.core.prompt_master import AMANDA_PERSONA_PROMPT

from langgraph.checkpoint.memory import MemorySaver
import operator
from app.services.google_calendar import check_availability, create_event
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)

# Checkpointer global para manter a memória enquanto o servidor estiver rodando
memory = MemorySaver()

from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: str
    intent: str
    thread_id: str

from app.api.endpoints.settings import load_config

def get_llm():
    cfg = load_config()
    model_name = cfg.get("model", "gpt-4o-mini")
    temp = float(cfg.get("temperature", 0.2))
    return ChatOpenAI(model=model_name, temperature=temp)

tools = [check_availability, create_event]

def extract_intent_node(state: AgentState):
    """Nó 1: Classifica a intenção do usuário."""
    messages = state['messages']
    last_msg = messages[-1].content
    
    prompt = f"""Analise a mensagem do paciente e classifique a intenção principal em apenas UMA das palavras abaixo:
- URGENCIA (se o paciente relatar falta de ar súbita, edema de glote, reação anafilática grave, dor intensa no peito, ou irritação extrema querendo falar com humano)
- AGENDAMENTO (se o paciente quiser marcar consulta, perguntar sobre horários)
- DUVIDA (se o paciente quiser tirar dúvidas, saber preços, localização, ou apenas dar um Oi)

Mensagem: "{last_msg}"
Classificação:"""
    
    logger.info("Extraindo intenção...")
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()
    
    if "URGENCIA" in response or "EMERGENCIA" in response:
        intent = "URGENCIA"
    elif "AGENDAR" in response or "AGENDAMENTO" in response:
        intent = "AGENDAMENTO"
    else:
        intent = "DUVIDA"
    return {"intent": intent}

def route_intent(state: AgentState) -> Literal["fetch_context", "schedule_flow", "urgency_flow"]:
    """Função de roteamento condicional baseada na intenção."""
    intent = state.get("intent")
    if intent == "URGENCIA":
        return "urgency_flow"
    if intent == "AGENDAMENTO":
        return "schedule_flow"
    return "fetch_context"

def urgency_flow_node(state: AgentState):
    """Nó de Alerta/Urgência: Gera mensagem de acolhimento emergencial e orienta buscar pronto-socorro."""
    msg = (
        "⚠️ Identifiquei que você pode estar passando por uma situação de urgência ou necessitando de atenção imediata.\n\n"
        "Se estiver com sintomas agudos (como falta de ar súbita ou reação alérgica severa), por favor, *procure o Pronto Socorro mais próximo imediatamente*.\n\n"
        "Já notifiquei nossa equipe clínica prioritariamente para assumir seu atendimento por aqui."
    )
    return {"messages": [AIMessage(content=msg)]}

def fetch_context_node(state: AgentState):
    """Nó 2a: Busca o contexto no RAG (para Dúvidas e Corpo Clínico)."""
    last_message = state['messages'][-1].content
    context = retrieve_context(last_message)
    return {"context": context}

def schedule_flow_node(state: AgentState):
    """Nó 2b: Fluxo dedicado para agendamento com corpo clínico e regras."""
    last_message = state['messages'][-1].content
    context = retrieve_context(f"{last_message} médicos convênios preços")
    return {"context": context}

async def generate_response_node(state: AgentState):
    """Nó 3: Gera a resposta da Amanda com base no contexto, intenção, perfil do paciente e histórico seguro."""
    intent = state.get('intent', 'duvidas_clinica')
    context = state.get('context', '')
    messages = state['messages']
    
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    
    # [MEMÓRIA DE LONGO PRAZO ESPECÍFICA] Recupera perfil cadastral prévio do paciente pelo thread_id (WhatsApp)
    patient_profile_str = ""
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
                
            if not active_contact:
                stmt_recent = select(Contact).order_by(Contact.updated_at.desc()).limit(1)
                res_recent = await session.execute(stmt_recent)
                active_contact = res_recent.scalars().first()

            if active_contact:
                profile_parts = []
                if active_contact.name:
                    profile_parts.append(f"Nome do Paciente: {active_contact.name}")
                if active_contact.insurance_operator:
                    profile_parts.append(f"Convênio: {active_contact.insurance_operator} (Plano: {active_contact.insurance_plan_name or 'Padrão'})")
                if active_contact.insurance_card_number:
                    profile_parts.append(f"Matrícula do Plano: {active_contact.insurance_card_number}")
                if active_contact.stage == "agendado":
                    profile_parts.append("Status: Já possui agendamento prévio ou histórico na clínica.")
                
                if profile_parts:
                    patient_profile_str = "📋 FICHA PRÉVIA DO PACIENTE (MEMÓRIA DE LONGO PRAZO):\n" + "\n".join(profile_parts) + "\n\n"
    except Exception as err:
        logger.debug(f"Aviso memória de longo prazo: {err}")

    # [CONSCIÊNCIA TEMPORAL DINÂMICA] Detecta o turno do dia no horário de Brasília (UTC-3)
    now_sp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    hora = now_sp.hour
    if 6 <= hora < 12:
        saudacao_turno = "MANHÃ (Use 'Bom dia' se for iniciar contato)"
    elif 12 <= hora < 18:
        saudacao_turno = "TARDE (Use 'Boa tarde' se for iniciar contato)"
    else:
        saudacao_turno = "NOITE/MADRUGADA (Use 'Boa noite' se for iniciar contato. Acolha informando que mesmo fora do expediente da recepção, você está à disposição para adiantar o agendamento)"

    enriched_context = f"DATA DE HOJE: {hoje} | TURNO ATUAL: {saudacao_turno}\n\n" + (patient_profile_str if patient_profile_str else "") + context

    system_prompt = AMANDA_PERSONA_PROMPT.format(
        rag_context=enriched_context,
        chat_history="O LangGraph gerencia este histórico.",
        user_message="[Leia o histórico acima para entender o fluxo atual e continuar a conversa.]"
    )
    # Filtra mensagens problemáticas (órfãs, dicts, RemoveMessage) para evitar erro 400 da OpenAI
    sanitized = []
    for m in messages:
        if not hasattr(m, "content"): # Ignora dicts corrompidos ou tipos desconhecidos
            continue
        from langchain_core.messages import RemoveMessage, ToolMessage, AIMessage, BaseMessage
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
    return {"messages": [response]}

def route_after_generation(state: AgentState) -> Literal["tools", "prune_history"]:
    """Se a LLM chamou uma tool, vá para o nó de tools. Caso contrário, vá para poda do histórico."""
    last_message = state['messages'][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "prune_history"

def prune_history_node(state: AgentState):
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
workflow.add_node("urgency_flow", urgency_flow_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_node("tools", tool_node)
workflow.add_node("prune_history", prune_history_node)

workflow.add_edge(START, "extract_intent")
workflow.add_conditional_edges("extract_intent", route_intent)
workflow.add_edge("fetch_context", "generate_response")
workflow.add_edge("schedule_flow", "generate_response")
workflow.add_edge("urgency_flow", "prune_history")

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
    # Garante que o checkpointer e o grafo estão inicializados
    if app_graph is None:
        await init_checkpointer()

    # [CAMADA 1: INPUT SHIELD] Interceptação de ataques adversariais / jailbreak
    from app.core.input_shield import detect_adversarial_attempt, sanitize_and_wrap_user_input
    
    if detect_adversarial_attempt(message):
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
    from app.services.semantic_cache import get_cached_response, set_cached_response
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
    
    # Grava no Cache Semântico em background para economia futura
    await set_cached_response(message, ai_content)
    
    return ai_content
