from sqlalchemy.future import select

from app.database import AsyncSessionLocal
from app.models.chat import Contact, Message, Appointment
import re


async def get_or_create_contact(phone_number: str, name: str = None) -> Contact:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Contact).where(Contact.phone_number == phone_number)
        )
        contact = result.scalar_one_or_none()

        if not contact:
            contact = Contact(phone_number=phone_number, name=name)
            session.add(contact)
            await session.commit()
            await session.refresh(contact)

        return contact


async def save_message(phone_number: str, text: str, sender: str, name: str = None):
    """
    Salva uma mensagem no banco. O sender deve ser 'paciente', 'ia' ou 'humano'.
    """
    contact = await get_or_create_contact(phone_number, name)

    async with AsyncSessionLocal() as session:
        msg = Message(contact_id=contact.id, text=text, sender=sender)
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
        return list(reversed(messages))  # Retorna na ordem cronológica


async def update_contact_stage_by_phone(phone_number: str, new_stage: str) -> bool:
    clean_phone = re.sub(r"\D", "", phone_number)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
        )
        contact = result.scalars().first()
        if contact:
            contact.stage = new_stage
            await session.commit()
            return True
        return False


async def update_contact_bot_active(phone_number: str, is_active: bool) -> bool:
    clean_phone = re.sub(r"\D", "", phone_number)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
        )
        contact = result.scalars().first()
        if contact:
            contact.bot_active = is_active
            await session.commit()
            return True
        return False


async def update_contact_insurance_info(phone_number: str, insurance_data: dict) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Contact).where(Contact.phone_number == phone_number)
        )
        contact = result.scalars().first()
        if contact:
            contact.insurance_operator = insurance_data.get("operator")
            contact.insurance_card_number = insurance_data.get("card_number")
            contact.insurance_plan_name = insurance_data.get("plan_name")
            contact.insurance_coverage = insurance_data.get("coverage_area")
            contact.insurance_accommodation = insurance_data.get("accommodation")
            if insurance_data.get("patient_name") and not contact.name:
                contact.name = insurance_data.get("patient_name")
            await session.commit()
            return True
        return False


async def record_nps_score(phone_number: str, nps_score: int) -> bool:
    clean_phone = re.sub(r"\D", "", phone_number)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
        )
        contact = result.scalars().first()
        if contact:
            result_apt = await session.execute(
                select(Appointment).where(
                    Appointment.contact_id == contact.id,
                    Appointment.nps_sent == True,
                    Appointment.nps_score == None
                ).order_by(Appointment.created_at.desc()).limit(1)
            )
            apt = result_apt.scalars().first()
            if apt:
                apt.nps_score = nps_score
                await session.commit()
                return True
        return False


async def create_or_get_appointment(phone_number: str, patient_name: str, start_dt, status="agendado"):
    import uuid
    clean_phone = re.sub(r"\D", "", phone_number) if phone_number else ""
    async with AsyncSessionLocal() as session:
        contact_id = None
        if clean_phone:
            result = await session.execute(
                select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
            )
            contact = result.scalars().first()
            if contact:
                contact_id = contact.id
                contact.stage = "agendado"

        if not contact_id:
            new_contact = Contact(
                id=str(uuid.uuid4()),
                phone_number=clean_phone or "0000000000",
                name=patient_name,
                stage="agendado",
            )
            session.add(new_contact)
            await session.flush()
            contact_id = new_contact.id

        existing = await session.execute(
            select(Appointment).where(
                Appointment.contact_id == contact_id,
                Appointment.appointment_time == start_dt,
                Appointment.status.in_(["agendado", "confirmado"])
            ).limit(1)
        )
        existing_apt = existing.scalars().first()
        
        if existing_apt:
            await session.commit()
            return existing_apt.id, True # (id, is_duplicate)
            
        new_apt = Appointment(
            contact_id=contact_id,
            patient_name=patient_name,
            appointment_time=start_dt,
            status=status
        )
        session.add(new_apt)
        await session.commit()
        await session.refresh(new_apt)
        return new_apt.id, False


async def update_appointment_google_event_id(appointment_id: str, event_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        apt = await session.get(Appointment, appointment_id)
        if apt:
            apt.google_event_id = event_id
            await session.commit()
            return True
        return False


async def get_contact_and_messages_for_learning(contact_id: str):
    async with AsyncSessionLocal() as session:
        contact = await session.get(Contact, contact_id)
        if not contact:
            return None, []

        stmt = select(Message).where(Message.contact_id == contact_id).order_by(Message.created_at)
        result = await session.execute(stmt)
        messages = result.scalars().all()
        return contact, messages


async def save_learning_suggestion(contact_id: str, patient_name: str, patient_phone: str, suggestion_text: str, context: str):
    from app.models.learning import LearningSuggestion
    async with AsyncSessionLocal() as session:
        new_suggestion = LearningSuggestion(
            contact_id=contact_id,
            patient_name=patient_name or "Desconhecido",
            patient_phone=patient_phone,
            suggestion_text=suggestion_text,
            context=context,
        )
        session.add(new_suggestion)
        await session.commit()


async def get_contacts_for_learning_evaluation(hours_ago: int = 2, limit: int = 10):
    from datetime import datetime, timedelta
    async with AsyncSessionLocal() as session:
        cutoff = datetime.utcnow() - timedelta(hours=hours_ago)
        stmt = select(Contact).where(Contact.updated_at >= cutoff).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


async def has_recent_learning_suggestion(contact_id: str, days_ago: int = 1) -> bool:
    from datetime import datetime, timedelta
    from app.models.learning import LearningSuggestion
    async with AsyncSessionLocal() as session:
        cutoff = datetime.utcnow() - timedelta(days=days_ago)
        stmt = select(LearningSuggestion).where(
            LearningSuggestion.contact_id == contact_id,
            LearningSuggestion.created_at >= cutoff,
        )
        result = await session.execute(stmt)
        return result.scalars().first() is not None
