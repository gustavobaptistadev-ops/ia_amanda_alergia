from collections.abc import Sequence
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """Estado serializável compartilhado pelos nós do grafo."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: str
    intent: str
    thread_id: str
    routing: dict
    record_validation: dict
    booking: dict
    patient_profile: dict
