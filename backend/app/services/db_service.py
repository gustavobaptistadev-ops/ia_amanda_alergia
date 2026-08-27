from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.chat import Contact, Message
from app.database import AsyncSessionLocal

async def get_or_create_contact(phone_number: str, name: str = None) -> Contact:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Contact).where(Contact.phone_number == phone_number))
        contact = result.scalar_one_or_none()
        
        if not contact:
            contact = Contact(phone_number=phone_number, name=name)
            session.add(contact)
            await session.commit()
            await session.refresh(contact)
        elif name and contact.name != name:
            # Update name if it changed and we didn't have it
            contact.name = name
            await session.commit()
            await session.refresh(contact)
            
        return contact

async def save_message(phone_number: str, text: str, sender: str, name: str = None):
    """
    Salva uma mensagem no banco. O sender deve ser 'paciente', 'ia' ou 'humano'.
    """
    contact = await get_or_create_contact(phone_number, name)
    
    async with AsyncSessionLocal() as session:
        msg = Message(
            contact_id=contact.id,
            text=text,
            sender=sender
        )
        session.add(msg)
        await session.commit()

async def get_chat_history(phone_number: str, limit: int = 15):
    """
    Recupera o histórico recente de mensagens do banco.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .join(Contact)
            .where(Contact.phone_number == phone_number)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages)) # Retorna na ordem cronológica
