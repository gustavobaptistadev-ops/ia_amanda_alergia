import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.chat import Contact, Message
from app.models.learning import LearningSuggestion, LearningStatus
from openai import AsyncOpenAI
import os
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def analyze_chat_for_learning(contact_id: str):
    """
    Called when a chat is finished or inactive. Evaluates if the AI made any mistakes
    or learned new user preferences, and generates a learning suggestion.
    """
    async with AsyncSessionLocal() as session:
        # Fetch the contact and messages
        contact = await session.get(Contact, contact_id)
        if not contact:
            return
        
        stmt = select(Message).where(Message.contact_id == contact_id).order_by(Message.created_at)
        result = await session.execute(stmt)
        messages = result.scalars().all()
        
        # We need a decent conversation length to evaluate anything
        if not messages or len(messages) < 4:
            return
            
        transcript = ""
        for m in messages:
            role = "Patient" if m.sender == "paciente" else "AI"
            # Decrypt the text if it's encrypted (Assuming EncryptedText is auto-decrypted when accessed)
            transcript += f"{role}: {m.text}\n"
            
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"""
    You are a Senior AI Reviewer for a medical clinic WhatsApp bot.
    Review the following conversation between the AI and a Patient.
    Identify if the AI made any factual mistakes, failed to answer a question, or if there is a patient preference that should be remembered globally.
    If there is a clear lesson or rule the AI should learn for future conversations to avoid mistakes, output it.
    If the conversation was perfect and standard, output exactly "NONE".
    
    Transcript:
    {transcript}
    
    Output format:
    If there is a lesson, write ONLY the suggestion in a clear rule format. Example: "O estacionamento da clnica fica na rua de trs."
    If no lesson, write: "NONE"
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2,
            max_tokens=200
        )
        
        suggestion = response.choices[0].message.content.strip()
        
        if suggestion and suggestion.upper() != "NONE":
            # Save the suggestion
            async with AsyncSessionLocal() as session:
                new_suggestion = LearningSuggestion(
                    contact_id=contact_id,
                    patient_name=contact.name or "Desconhecido",
                    patient_phone=contact.phone_number,
                    suggestion_text=suggestion,
                    context=f"Extraído automaticamente do chat"
                )
                session.add(new_suggestion)
                await session.commit()
                logger.info(f"Nova sugestão de aprendizado criada para o contato {contact_id}")
    except Exception as e:
        logger.error(f"Erro ao analisar chat para aprendizado: {e}")

async def evaluate_recent_chats():
    async with AsyncSessionLocal() as session:
        # Pega os 10 contatos atualizados nas ultimas 2 horas
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        stmt = select(Contact).where(Contact.updated_at >= two_hours_ago).limit(10)
        result = await session.execute(stmt)
        recent_contacts = result.scalars().all()
        
        for c in recent_contacts:
            # Verifica se j� gerou sugest�o de aprendizado recente para evitar duplica��o (nas �ltimas 24h)
            last_day = datetime.utcnow() - timedelta(days=1)
            stmt_sug = select(LearningSuggestion).where(
                LearningSuggestion.contact_id == c.id,
                LearningSuggestion.created_at >= last_day
            )
            sug_result = await session.execute(stmt_sug)
            if sug_result.scalars().first():
                continue # J� avaliou hoje
            
            # Executa a avalia��o
            await analyze_chat_for_learning(c.id)

