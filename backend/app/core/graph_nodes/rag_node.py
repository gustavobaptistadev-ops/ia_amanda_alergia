from app.core.state import AgentState
from app.core.rag import retrieve_context

async def fetch_context_node(state: AgentState):
    """Consulta a base de conhecimento sem alterar o histórico da conversa."""
    """Nó 2a: Busca o contexto no RAG (para Dúvidas e Corpo Clínico)."""
    last_message = state["messages"][-1].content
    from app.services.semantic_cache import get_cached_response

    cached_reply = await get_cached_response(last_message)
    if cached_reply:
        return {"context": f"[CACHED_PUBLIC_RESPONSE]\\n{cached_reply}"}
    context = retrieve_context(last_message)
    return {"context": context}
