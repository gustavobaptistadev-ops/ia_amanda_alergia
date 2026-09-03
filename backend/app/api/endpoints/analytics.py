"""Indicadores operacionais calculados exclusivamente com dados persistidos."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat import Appointment, Contact, Message

router = APIRouter()


@router.get("/overview")
async def get_analytics_overview(db: AsyncSession = Depends(get_db)):
    """Retorna metricas executivas calculadas com dados persistidos."""
    # Valores de demonstração são proibidos: falhas devem ser observáveis pelo operador.
    total_contacts = await db.scalar(select(func.count(Contact.id))) or 0
    scheduled = await db.scalar(select(func.count(Contact.id)).where(Contact.stage == "agendado")) or 0
    human = await db.scalar(select(func.count(Contact.id)).where(Contact.bot_active == False)) or 0
    messages = await db.scalar(select(func.count(Message.id))) or 0
    reminders = await db.scalar(select(func.count(Appointment.id)).where(Appointment.reminder_24h_sent == True)) or 0
    rate = round(scheduled / total_contacts * 100, 1) if total_contacts else 0.0
    cost_usd = round(messages * 0.0008, 4)
    cost_brl = round(cost_usd * 5.75, 2)
    savings = round(max(0, total_contacts * 3.50 - cost_brl), 2)
    return {
        "total_pacientes": total_contacts,
        "consultas_agendadas": scheduled,
        "taxa_conversao": f"{rate}%",
        "atendimentos_humanos": human,
        "total_mensagens": messages,
        "lembretes_disparados": reminders,
        "no_shows_prevenidos_estimados": int(reminders * 0.85),
        "custo_estimado_usd": f"${cost_usd:.3f}",
        "custo_estimado_brl": f"R$ {cost_brl:.2f}".replace(".", ","),
        "economia_gerada_brl": f"R$ {savings:.2f}".replace(".", ","),
    }
