import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def analyze_chat_for_learning(contact_id: str):
    """
    Called when a chat is finished or inactive. Evaluates if the AI made any mistakes
    or learned new user preferences, and generates a learning suggestion.
    """
    from app.services.db_service import get_contact_and_messages_for_learning, save_learning_suggestion
    contact, messages = await get_contact_and_messages_for_learning(contact_id)

    if not contact or not messages or len(messages) < 4:
        return

    transcript = ""
    for m in messages:
        role = "Patient" if m.sender == "paciente" else "AI"
        transcript += f"{role}: {m.text}\n"

    from app.services.langflow_client import evaluate_transcript_via_langflow
    
    try:
        suggestion = await evaluate_transcript_via_langflow(transcript, contact_id)
        if suggestion and suggestion.upper() != "NONE":
            await save_learning_suggestion(
                contact_id=contact_id,
                patient_name=contact.name,
                patient_phone=contact.phone_number,
                suggestion_text=suggestion,
                context="Extraído automaticamente do chat via Langflow"
            )
            logger.info(f"Nova sugestão de aprendizado criada para o contato {contact_id}")

    except Exception as e:
        logger.error(f"Erro ao analisar chat para aprendizado: {e}")

async def evaluate_recent_chats():
    from app.services.db_service import get_contacts_for_learning_evaluation, has_recent_learning_suggestion
    recent_contacts = await get_contacts_for_learning_evaluation(hours_ago=2, limit=10)

    for c in recent_contacts:
        if await has_recent_learning_suggestion(c.id, days_ago=1):
            continue
        await analyze_chat_for_learning(c.id)
