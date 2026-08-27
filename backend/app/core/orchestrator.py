import os
import logging
from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
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

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage

# Removido: memory = MemorySaver()
# Compila o grafo SEM checkpointer (memória será injetada manualmente do Postgres)
app_graph = workflow.compile()

async def process_user_message(thread_id: str, message: str) -> str:
    from app.services.db_service import get_chat_history
    
    # Busca histórico real do banco de dados (últimas 15 mensagens)
    db_messages = await get_chat_history(thread_id, limit=15)
    
    langchain_messages = []
    for m in db_messages:
        if m.sender == 'paciente':
            # Ignora a última mensagem do banco porque vamos adicioná-la abaixo
            # Ops, a última já é essa?
            # O webhook salva a msg do paciente ANTES de chamar process_user_message.
            # Então a mensagem atual JÁ ESTÁ em db_messages.
            # Para o LangGraph não processar duplicado, pegamos tudo do banco.
            langchain_messages.append(HumanMessage(content=m.text))
        else:
            langchain_messages.append(AIMessage(content=m.text))
            
    # Se por acaso a mensagem atual ainda não foi salva (fallback de segurança)
    if not langchain_messages or langchain_messages[-1].content != message:
        langchain_messages.append(HumanMessage(content=message))
    
    input_state = {"messages": langchain_messages}
    
    logger.info(f"LangGraph processando thread {thread_id} puxando {len(langchain_messages)} msgs do Postgres.")
    
    # Executa sem 'config' de thread_id, já que não usamos checkpointer interno
    final_state = await app_graph.ainvoke(input_state)
    
    return final_state['messages'][-1].content
