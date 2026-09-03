import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.calendar_links import build_google_calendar_url
from app.core.clinic_location import CLINIC_ADDRESS
from app.database import get_db
from app.models.chat import Appointment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/p/{appointment_id}")
async def redirect_to_personal_calendar(appointment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalars().first()
    now = datetime.datetime.utcnow()
    if not appointment or appointment.status in {"cancelado", "concluido"} or appointment.appointment_time < now - datetime.timedelta(days=1):
        logger.warning("Tentativa de uso de link de agenda inválido, cancelado ou expirado")
        raise HTTPException(status_code=404, detail="Link de agenda inválido ou expirado")

    url = build_google_calendar_url(
        appointment.appointment_time.strftime("%Y-%m-%d"),
        appointment.appointment_time.strftime("%H:%M"),
        appointment.patient_name,
        CLINIC_ADDRESS,
    )
    return RedirectResponse(url, status_code=302)
