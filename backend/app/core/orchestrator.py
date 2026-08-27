import os
import logging
from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from app.core.rag import retrieve_context
from app.core.prompt_master import AMANDA_PERSONA_PROMPT

import redis.asyncio as redis
from langgraph.checkpoint.redis import AsyncRedisSaver
import operator
from app.services.google_calendar import check_availability, create_event
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
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
    
    # Adicionando a instrução do sistema no topo
    conversation = [SystemMessage(content=system_prompt)] + list(messages)
    logger.info("Gerando resposta da LLM (Amanda) com tools...")
    response = llm_with_tools.invoke(conversation)
    return {"messages": [response]}

def route_after_generation(state: AgentState) -> Literal["tools", "__end__"]:
    """Se a LLM chamou uma tool, vá para o nó de tools. Caso contrário, fim."""
    last_message = state['messages'][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "__end__"

# Montagem do Grafo Avançado
workflow = StateGraph(AgentState)
tool_node = ToolNode(tools)

workflow.add_node("extract_intent", extract_intent_node)
workflow.add_node("fetch_context", fetch_context_node)
workflow.add_node("schedule_flow", schedule_flow_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "extract_intent")
workflow.add_conditional_edges("extract_intent", route_intent)
workflow.add_edge("fetch_context", "generate_response")
workflow.add_edge("schedule_flow", "generate_response")

workflow.add_conditional_edges(
    "generate_response",
    route_after_generation
)
# Após a ferramenta rodar, devolva para a LLM gerar a resposta final com o resultado
workflow.add_edge("tools", "generate_response")

async def process_user_message(thread_id: str, message: str) -> str:
    async with redis.Redis.from_url(REDIS_URL) as redis_conn:
        checkpointer = AsyncRedisSaver(redis_conn)
        app_graph = workflow.compile(checkpointer=checkpointer)
        
        config = {"configurable": {"thread_id": thread_id}}
        input_state = {"messages": [HumanMessage(content=message)]}
        
        logger.info(f"LangGraph processando thread {thread_id} com nova arquitetura de Nodes.")
        final_state = await app_graph.ainvoke(input_state, config=config)
        
        return final_state['messages'][-1].content
