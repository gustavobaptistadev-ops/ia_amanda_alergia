from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat import Appointment, Contact

router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Retorna estatisticas calculadas exclusivamente a partir do banco real."""
    total_contacts = await db.scalar(select(func.count(Contact.id))) or 0
    appointments = await db.scalar(select(func.count(Appointment.id)).where(Appointment.status == "agendado")) or 0
    human_contacts = await db.scalar(select(func.count(Contact.id)).where(Contact.bot_active == False)) or 0
    return {"novos_contatos": total_contacts, "agendamentos": appointments, "em_atendimento": human_contacts}


@router.get("/conversations")
async def get_conversations(db: AsyncSession = Depends(get_db)):
    """Retorna contatos reais, sem dados simulados."""
    result = await db.execute(select(Contact).limit(100))
    return [{"id": str(c.id), "name": c.name or c.phone_number, "last_message": "", "time": "", "status": "IA" if c.bot_active else "Humano"} for c in result.scalars().all()]


@router.get("/kanban")
async def get_kanban_patients(db: AsyncSession = Depends(get_db)):
    """Retorna pacientes reais divididos por etapa do atendimento."""
    result = await db.execute(select(Contact))
    columns = {"triagem": [], "agendado": [], "pos_consulta": [], "retorno": [], "atendimento_humano": []}
    for c in result.scalars().all():
        name = c.name or c.phone_number
        if not c.bot_active:
            columns["atendimento_humano"].append(name)
        elif c.stage in columns:
            columns[c.stage].append(name)
        else:
            columns["triagem"].append(name)
    return [
        {"title": "Novo Contato / Triagem", "color": "bg-blue-500", "patients": columns["triagem"]},
        {"title": "Agendamento Confirmado", "color": "bg-emerald-500", "patients": columns["agendado"]},
        {"title": "Pos-consulta / Feedback", "color": "bg-purple-500", "patients": columns["pos_consulta"]},
        {"title": "Retorno de Paciente", "color": "bg-amber-500", "patients": columns["retorno"]},
        {"title": "Atendimento Humano", "color": "bg-rose-500", "patients": columns["atendimento_humano"]},
    ]
