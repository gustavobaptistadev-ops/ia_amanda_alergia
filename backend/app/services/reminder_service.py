import logging
from datetime import datetime, timedelta
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.chat import Appointment, Contact, SystemLog
from app.services.evolution_api import send_text_message
from app.services.message_processor import save_message

logger = logging.getLogger(__name__)

async def check_and_send_reminders():
    """
    Varre os agendamentos no banco e executa o ciclo completo de hospitalidade médica:
    1. Preparo de Exames de Alergia (5 dias antes) - Reforço para suspender antialérgicos
    2. Lembrete Proativo de 24 horas antes
    3. Lembrete de Rota e Manobrista de 2 horas antes
    4. Follow-up Clínico Pós-Consulta (48 horas após a consulta realizada)
    """
    logger.info("Iniciando rotina de checagem de lembretes e follow-up clínico...")
    now = datetime.utcnow()
    
    # 1. Range para Preparo de Exames (5 dias antes -> entre 118h e 122h no futuro)
    window_prep_start = now + timedelta(days=4, hours=22)
    window_prep_end = now + timedelta(days=5, hours=2)

    # 2. Range para 24 horas (entre 23h e 25h no futuro)
    window_24h_start = now + timedelta(hours=23)
    window_24h_end = now + timedelta(hours=25)

    # 3. Range para 2 horas (entre 1h30 e 2h30 no futuro)
    window_2h_start = now + timedelta(minutes=90)
    window_2h_end = now + timedelta(minutes=150)

    # 4. Range para Follow-up Clínico 48h pós-consulta (consultas ocorridas entre 47h e 50h atrás)
    window_followup_start = now - timedelta(hours=50)
    window_followup_end = now - timedelta(hours=47)

    async with AsyncSessionLocal() as session:
        try:
            total_sent = 0

            # ----------------------------------------------------
            # ETAPA 1: PREPARO DE TESTES DE ALERGIA (5 DIAS ANTES)
            # ----------------------------------------------------
            stmt_prep = (
                select(Appointment)
                .options(selectinload(Appointment.contact))
                .where(
                    Appointment.status.in_(["agendado", "confirmado"]),
                    Appointment.prep_reminder_sent == False,
                    Appointment.appointment_time >= window_prep_start,
                    Appointment.appointment_time <= window_prep_end
                )
            )
            res_prep = await session.execute(stmt_prep)
            appointments_prep = res_prep.scalars().all()

            for appt in appointments_prep:
                if appt.contact and appt.contact.phone_number:
                    time_fmt = appt.appointment_time.strftime("%d/%m às %H:%M")
                    msg = (
                        f"Olá, {appt.patient_name}! Aqui é a Amanda da Clínica Respirar. 🌻\n\n"
                        f"Sua consulta está agendada para o dia *{time_fmt}*.\n\n"
                        "💡 *Orientação Importante de Preparo:*\n"
                        "Caso o seu médico solicite a realização de *Testes Alérgicos (Prick Test)* durante a consulta, é fundamental suspender o uso de antialérgicos orais (como Desloratadina, Ebastina, Fexofenadina ou Loratadina) de 5 a 7 dias antes para não interferir no resultado do exame.\n\n"
                        "Se tiver qualquer dúvida sobre sua medicação, pode me chamar por aqui!"
                    )
                    await send_text_message(appt.contact.phone_number, msg)
                    await save_message(appt.contact.phone_number, msg, sender='ia')
                    appt.prep_reminder_sent = True
                    total_sent += 1
                    session.add(SystemLog(
                        category="cron_lembretes",
                        level="INFO",
                        title=f"Preparo de Exames enviado: {appt.patient_name}",
                        detail=f"Orientação de suspensão de antialérgicos para {appt.contact.phone_number[:6]}****"
                    ))

            # ----------------------------------------------------
            # ETAPA 2: LEMBRETE DE 24 HORAS ANTES
            # ----------------------------------------------------
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
                        f"Oi, {appt.patient_name}! Tudo bem? 🌿\n\n"
                        f"Passando para lembrar com carinho da sua consulta amanhã, dia *{time_fmt}*, na Clínica Respirar.\n\n"
                        "Podemos confirmar a sua presença? Basta me responder com um 'Sim, confirmo' ou me avisar caso precise de outro horário!"
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

            # ----------------------------------------------------
            # ETAPA 3: LEMBRETE DE 2 HORAS (ROTA & MANOBRISTA)
            # ----------------------------------------------------
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
                        detail=f"Disparo com rota e manobrista para {appt.contact.phone_number[:6]}****"
                    ))

            # ----------------------------------------------------
            # ETAPA 4: FOLLOW-UP CLÍNICO PÓS-CONSULTA (48 HORAS)
            # ----------------------------------------------------
            stmt_followup = (
                select(Appointment)
                .options(selectinload(Appointment.contact))
                .where(
                    Appointment.status.in_(["confirmado", "concluido", "agendado"]),
                    Appointment.follow_up_sent == False,
                    Appointment.appointment_time >= window_followup_start,
                    Appointment.appointment_time <= window_followup_end
                )
            )
            res_followup = await session.execute(stmt_followup)
            appointments_followup = res_followup.scalars().all()

            for appt in appointments_followup:
                if appt.contact and appt.contact.phone_number:
                    msg = (
                        f"Olá, {appt.patient_name}! Aqui é a Amanda da Clínica Respirar. 🌻\n\n"
                        "Passando para saber como você está se sentindo após a sua consulta e com o início das orientações do médico!\n\n"
                        "Ficou com alguma dúvida sobre seu plano de tratamento ou receitas? Nossa equipe médica está à disposição para cuidar de você."
                    )
                    await send_text_message(appt.contact.phone_number, msg)
                    await save_message(appt.contact.phone_number, msg, sender='ia')
                    appt.follow_up_sent = True
                    total_sent += 1
                    session.add(SystemLog(
                        category="cron_lembretes",
                        level="SUCCESS",
                        title=f"Follow-up 48h enviado: {appt.patient_name}",
                        detail=f"Acolhimento pós-consulta enviado para {appt.contact.phone_number[:6]}****"
                    ))

            session.add(SystemLog(
                category="cron_lembretes",
                level="SUCCESS",
                title="Varredura de Lembretes & Follow-up Concluída",
                detail=f"Lote verificado com sucesso. Total de disparos realizados: {total_sent}."
            ))
            await session.commit()
            logger.info(f"Rotina de lembretes finalizada com sucesso. Total de disparos: {total_sent}")
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
