import logging
from datetime import datetime, timedelta
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.chat import Appointment, Contact, SystemLog

logger = logging.getLogger(__name__)

async def check_and_send_reminders():
    """
    Varre os agendamentos no banco e envia lembretes proativos:
    - 24 horas antes da consulta
    - 2 horas antes da consulta
    """
    logger.info("Iniciando rotina de checagem de lembretes de consulta...")
    now = datetime.utcnow()
    
    # Range para 24 horas (entre 23h e 25h no futuro)
    window_24h_start = now + timedelta(hours=23)
    window_24h_end = now + timedelta(hours=25)

    # Range para 2 horas (entre 1h30 e 2h30 no futuro)
    window_2h_start = now + timedelta(minutes=90)
    window_2h_end = now + timedelta(minutes=150)

    async with AsyncSessionLocal() as session:
        try:
            total_sent = 0
            # 1. Checar lembretes de 24h
            stmt_24h = (
                select(Appointment)
                .options(selectinload(Appointment.contact))
                .where(
                    Appointment.status == "agendado",
                    Appointment.reminder_24h_sent == False,
                    Appointment.appointment_time >= window_24h_start,
                    Appointment.appointment_time <= window_24h_end
                )
            )
            res_24h = await session.execute(stmt_24h)
            appointments_24h = res_24h.scalars().all()

            for appt in appointments_24h:
                if appt.contact and appt.contact.phone_number:
                    time_fmt = appt.appointment_time.strftime("%d/%m às %H:%M")
                    msg = (
                        f"Oi, {appt.patient_name}! Tudo bem por aí? 🌿\n\n"
                        f"Passando para lembrar com carinho da sua consulta amanhã, dia *{time_fmt}*, na Clínica Respirar.\n\n"
                        "Podemos confirmar a sua presença? Basta me responder com um 'Sim, confirmo' ou me avisar caso precise de outro dia!"
                    )
                    await send_text_message(appt.contact.phone_number, msg)
                    await save_message(appt.contact.phone_number, msg, sender='ia')
                    appt.reminder_24h_sent = True
                    total_sent += 1
                    session.add(SystemLog(
                        category="cron_lembretes",
                        level="INFO",
                        title=f"Lembrete 24h enviado: {appt.patient_name}",
                        detail=f"Disparo via WhatsApp para {appt.contact.phone_number[:6]}****"
                    ))
                    logger.info(f"Lembrete 24h enviado para {appt.contact.phone_number}")

            # 2. Checar lembretes de 2h
            stmt_2h = (
                select(Appointment)
                .options(selectinload(Appointment.contact))
                .where(
                    Appointment.status.in_(["agendado", "confirmado"]),
                    Appointment.reminder_2h_sent == False,
                    Appointment.appointment_time >= window_2h_start,
                    Appointment.appointment_time <= window_2h_end
                )
            )
            res_2h = await session.execute(stmt_2h)
            appointments_2h = res_2h.scalars().all()

            for appt in appointments_2h:
                if appt.contact and appt.contact.phone_number:
                    time_fmt = appt.appointment_time.strftime("%H:%M")
                    msg = (
                        f"Oi, {appt.patient_name}! 🩵\n\n"
                        f"Sua consulta com o especialista é hoje às *{time_fmt}* (daqui a pouquinho!).\n\n"
                        "📍 *Endereço:* Av. Paulista, 1000 - Conjunto 1204 (Temos manobrista no local).\n"
                        "Nossa equipe já está te esperando com um café quentinho. Tenha uma excelente vinda!"
                    )
                    await send_text_message(appt.contact.phone_number, msg)
                    await save_message(appt.contact.phone_number, msg, sender='ia')
                    appt.reminder_2h_sent = True
                    total_sent += 1
                    session.add(SystemLog(
                        category="cron_lembretes",
                        level="INFO",
                        title=f"Lembrete 2h enviado: {appt.patient_name}",
                        detail=f"Disparo com rota da clínica para {appt.contact.phone_number[:6]}****"
                    ))
                    logger.info(f"Lembrete 2h enviado para {appt.contact.phone_number}")

            session.add(SystemLog(
                category="cron_lembretes",
                level="SUCCESS",
                title="Varredura de Lembretes Concluída",
                detail=f"Lote verificado com sucesso. Total de lembretes disparados: {total_sent}."
            ))
            await session.commit()
            logger.info("Rotina de lembretes finalizada com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao processar lembretes: {e}")
            try:
                session.add(SystemLog(
                    category="cron_lembretes",
                    level="ERROR",
                    title="Erro na Execução do Lote",
                    detail=str(e)
                ))
                await session.commit()
            except:
                pass
