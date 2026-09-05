import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.chat import Appointment, Contact

logger = logging.getLogger(__name__)
router = APIRouter()


class AppointmentCreate(BaseModel):
    patient_name: str
    phone_number: str
    appointment_time: datetime
    status: str = "agendado"


class AppointmentUpdate(BaseModel):
    patient_name: str | None = None
    appointment_time: datetime | None = None
    status: str | None = None


class AppointmentResponse(BaseModel):
    id: str
    contact_id: str
    patient_name: str
    phone_number: str
    appointment_time: datetime
    status: str
    created_at: datetime


@router.get("/")
async def list_appointments(
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
    date: str | None = Query(None),
):
    """Lista consultas agendadas ordenadas por horário."""
    query = select(Appointment, Contact.phone_number).join(
        Contact, Appointment.contact_id == Contact.id
    )

    if status:
        query = query.where(Appointment.status == status)

    result = await db.execute(query.order_by(Appointment.appointment_time.asc()))
    rows = result.all()

    appointments = []
    for appt, phone in rows:
        appointments.append(
            {
                "id": appt.id,
                "contact_id": appt.contact_id,
                "patient_name": appt.patient_name,
                "phone_number": phone,
                "appointment_time": appt.appointment_time.isoformat(),
                "status": appt.status,
                "created_at": appt.created_at.isoformat() if appt.created_at else None,
            }
        )
    return appointments


@router.post("/")
async def create_appointment(data: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    """Cria uma consulta manualmente pelo painel."""
    # Busca ou cria o contato pelo telefone
    result = await db.execute(
        select(Contact).where(Contact.phone_number == data.phone_number)
    )
    contact = result.scalars().first()

    if not contact:
        contact = Contact(
            phone_number=data.phone_number,
            name=data.patient_name,
            stage="agendado",
            bot_active=True,
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
    else:
        contact.stage = "agendado"
        if not contact.name:
            contact.name = data.patient_name
        await db.commit()

    new_appt = Appointment(
        contact_id=contact.id,
        patient_name=data.patient_name,
        appointment_time=data.appointment_time,
        status=data.status,
    )
    db.add(new_appt)
    await db.commit()
    await db.refresh(new_appt)

    return {
        "status": "ok",
        "message": "Consulta criada com sucesso!",
        "appointment": {
            "id": new_appt.id,
            "patient_name": new_appt.patient_name,
            "appointment_time": new_appt.appointment_time.isoformat(),
            "status": new_appt.status,
        },
    }


@router.put("/{appointment_id}")
async def update_appointment(
    appointment_id: str, data: AppointmentUpdate, db: AsyncSession = Depends(get_db)
):
    """Atualiza dados, horário ou status de uma consulta."""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalars().first()

    if not appt:
        raise HTTPException(status_code=404, detail="Consulta não encontrada.")

    if data.patient_name is not None:
        appt.patient_name = data.patient_name
    if data.appointment_time is not None:
        appt.appointment_time = data.appointment_time
    if data.status is not None:
        appt.status = data.status

    await db.commit()
    await db.refresh(appt)

    return {
        "status": "ok",
        "message": "Consulta atualizada com sucesso!",
        "appointment": {
            "id": appt.id,
            "patient_name": appt.patient_name,
            "appointment_time": appt.appointment_time.isoformat(),
            "status": appt.status,
        },
    }


@router.delete("/{appointment_id}")
async def cancel_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """Cancela uma consulta médica."""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalars().first()

    if not appt:
        raise HTTPException(status_code=404, detail="Consulta não encontrada.")

    appt.status = "cancelado"
    await db.commit()
    return {"status": "ok", "message": "Consulta cancelada."}
