import os
import logging
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

tools = [check_availability, create_event]
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
llm_with_tools = llm.bind_tools(tools)

def extract_intent_node(state: AgentState):
    """Nó 1: Classifica a intenção do usuário."""
    messages = state['messages']
    last_msg = messages[-1].content
    
    prompt = f"""Analise a mensagem do paciente e classifique a intenção principal em apenas UMA das palavras abaixo:
- AGENDAMENTO (se o paciente quiser marcar consulta, perguntar sobre horários)
- DUVIDA (se o paciente quiser tirar dúvidas, saber preços, localização, ou apenas dar um Oi)

Mensagem: "{last_msg}"
Classificação:"""
    
    logger.info("Extraindo intenção...")
    response = llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()
    
    intent = "AGENDAMENTO" if "AGENDAR" in response or "AGENDAMENTO" in response else "DUVIDA"
    return {"intent": intent}

def route_intent(state: AgentState) -> Literal["fetch_context", "schedule_flow"]:
    """Função de roteamento condicional baseada na intenção."""
    if state.get("intent") == "AGENDAMENTO":
        return "schedule_flow"
    return "fetch_context"

def fetch_context_node(state: AgentState):
    """Nó 2a: Busca o contexto no RAG (para Dúvidas)."""
    last_message = state['messages'][-1].content
    context = retrieve_context(last_message)
    return {"context": context}

def schedule_flow_node(state: AgentState):
    """Nó 2b: Fluxo dedicado para agendamento."""
    context = retrieve_context("convênios e preços")
    return {"context": context}

def generate_response_node(state: AgentState):
    """Nó 3: Gera a resposta da IA com suporte a tools."""
    messages = state['messages']
    context = state.get('context', '')
    
    from datetime import datetime
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = AMANDA_PERSONA_PROMPT.format(
        rag_context=f"DATA DE HOJE: {hoje}\n" + context,
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
    response = llm_with_tools.invoke(conversation)
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
        # Pega todas as mensagens antigas, deixando apenas as 10 mais recentes
        messages_to_remove = messages[:-10]
        return {"messages": [RemoveMessage(id=m.id) for m in messages_to_remove if m.id is not None]}
    return {}

# Montagem do Grafo Avançado
workflow = StateGraph(AgentState)
tool_node = ToolNode(tools)

workflow.add_node("extract_intent", extract_intent_node)
workflow.add_node("fetch_context", fetch_context_node)
workflow.add_node("schedule_flow", schedule_flow_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_node("tools", tool_node)
workflow.add_node("prune_history", prune_history_node)

workflow.add_edge(START, "extract_intent")
workflow.add_conditional_edges("extract_intent", route_intent)
workflow.add_edge("fetch_context", "generate_response")
workflow.add_edge("schedule_flow", "generate_response")

workflow.add_conditional_edges(
    "generate_response",
    route_after_generation
)
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
        
        # Cria as tabelas necessárias no banco usando uma conexão com autocommit=True 
        # para evitar o erro "CREATE INDEX CONCURRENTLY cannot run inside a transaction block"
        async with await psycopg.AsyncConnection.connect(db_url, autocommit=True) as conn:
            temp_saver = AsyncPostgresSaver(conn)
            await temp_saver.setup()
            
        # Agora inicializa o pool e o checkpointer final
        pool = AsyncConnectionPool(db_url, max_size=10, open=False)
        await pool.open()
        
        _checkpointer = AsyncPostgresSaver(pool)
        
        # Compila o grafo usando o checkpointer nativo do LangGraph
        workflow.add_edge("tools", "generate_response")
        app_graph = workflow.compile(checkpointer=_checkpointer)

async def process_user_message(thread_id: str, message: str) -> str:
    # Garante que o checkpointer e o grafo estão inicializados
    if app_graph is None:
        await init_checkpointer()
        
    config = {"configurable": {"thread_id": thread_id}}
    
    # Com o checkpointer oficial, não precisamos carregar o histórico manualmente do banco de dados (tabela messages)
    # O próprio LangGraph vai gerenciar o histórico nas tabelas `checkpoints`!
    input_state = {"messages": [HumanMessage(content=message)]}
    
    logger.info(f"LangGraph processando thread {thread_id} com AsyncPostgresSaver.")
    
    final_state = await app_graph.ainvoke(input_state, config=config)
    
    return final_state['messages'][-1].content
