import os
import datetime
import json
import re
import logging
from langchain_core.tools import tool

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    service_account = None
    build = None

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
# O arquivo credentials.json deverá ser salvo na pasta backend/
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '../../credentials.json')

# O ID da agenda (pode ser "primary" se for a conta dona, mas como é Service Account, precisamos do e-mail da agenda)
# O usuário precisará compartilhar a agenda com o e-mail do Service Account.
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

def get_calendar_service():
    """Autentica e retorna o serviço da API do Google Calendar."""
    creds = None
    if os.getenv("GOOGLE_CREDENTIALS_JSON"):
        try:
            creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Erro ao ler GOOGLE_CREDENTIALS_JSON: {e}")
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Erro ao ler credentials.json: {e}")
            
    if not creds:
        logger.warning("Credenciais do Google não encontradas. Integração com Google Calendar operando em modo Simulação.")
        return None

    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Erro ao inicializar Google Calendar: {e}")
        return None

@tool
def check_availability(date_str: str, period: str = "todos") -> str:
    """
    Checa a disponibilidade na agenda para uma data específica (YYYY-MM-DD).
    Opcionalmente filtra por período preferido ('manha', 'tarde' ou 'todos').
    """
    weekdays_pt = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    try:
        dt_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        dia_da_semana_nome = weekdays_pt[dt_obj.weekday()]
        data_formatada = dt_obj.strftime("%d/%m/%Y")
    except Exception:
        dia_da_semana_nome = ""
        data_formatada = date_str

    service = get_calendar_service()
    if not service:
        # Modo Simulação com suporte a filtro de período e ancoragem de dia da semana
        header = f"Horários livres para {dia_da_semana_nome}, dia {data_formatada} ({date_str})"
        if period.lower() == "manha":
            return f"Os seguintes horários da MANHÃ estão livres para {dia_da_semana_nome} ({data_formatada}): 09:00 e 10:30."
        elif period.lower() == "tarde":
            return f"Os seguintes horários da TARDE estão livres para {dia_da_semana_nome} ({data_formatada}): 14:00 e 15:30."
        return f"Os seguintes horários estão livres para {dia_da_semana_nome} ({data_formatada}): 09:00, 10:30, 14:00 e 15:30."

    try:
        start_time = f"{date_str}T00:00:00-03:00"
        end_time = f"{date_str}T23:59:59-03:00"

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Grade de horários de trabalho da clínica:
        base_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        weekday = base_date.weekday() # 0 = Segunda, 5 = Sábado, 6 = Domingo

        # Domingo (6) a clínica não abre
        if weekday == 6:
            return f"A clínica não realiza atendimentos aos domingos. Por favor, consulte horários para dias úteis (segunda a sexta) ou sábados pela manhã."

        # Sábado (5): Atendimento reduzido das 08h às 12h
        if weekday == 5:
            horarios_trabalho = ["08:30", "09:30", "10:30", "11:30"]
        else:
            # Segunda a Sexta: Atendimento normal
            horarios_trabalho = [
                "09:00", "10:00", "11:00", 
                "14:00", "15:00", "16:00", "17:00"
            ]
        
        # Filtra pelo turno solicitado pelo paciente
        if period and period.lower() in ["manha", "manhã"]:
            horarios_trabalho = [h for h in horarios_trabalho if int(h.split(":")[0]) < 12]
        elif period and period.lower() == "tarde":
            horarios_trabalho = [h for h in horarios_trabalho if int(h.split(":")[0]) >= 12]

        ocupados_ranges = []
        for event in events:
            start = event['start'].get('dateTime')
            end = event['end'].get('dateTime')
            
            if start and end:
                try:
                    s_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                    e_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
                    ocupados_ranges.append((s_dt, e_dt))
                except Exception:
                    pass

        livres = []
        
        for h in horarios_trabalho:
            slot_time = datetime.datetime.strptime(h, "%H:%M").time()
            slot_start = datetime.datetime.combine(base_date, slot_time).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
            slot_end = slot_start + datetime.timedelta(hours=1)
            
            conflito = False
            for (s_dt, e_dt) in ocupados_ranges:
                if slot_start < e_dt and slot_end > s_dt:
                    conflito = True
                    break
            
            agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
            if slot_start < agora:
                conflito = True

            if not conflito:
                livres.append(h)
        
        if livres:
            # Retorna até 3 opções para visual leve no WhatsApp
            sugestoes = livres[:3]
            period_label = f" ({period.lower()})" if period != "todos" else ""
            return f"Horários livres para {date_str}{period_label}: " + ", ".join(sugestoes)
        else:
            # [PROATIVIDADE 10/10] Se não houver horários, busca no próximo dia útil para não deixar o paciente sem opção
            next_day = base_date + datetime.timedelta(days=1)
            if next_day.weekday() == 6: # Se for domingo, pula pra segunda
                next_day += datetime.timedelta(days=1)
            elif next_day.weekday() == 5: # Se for sábado, busca na segunda
                next_day += datetime.timedelta(days=2)
            next_date_str = next_day.strftime("%Y-%m-%d")
            return (
                f"A agenda para {date_str} no período ({period}) já está completa. "
                f"Por favor, sugira ao paciente uma alternativa com carinho (ex: no próximo dia útil {next_date_str} ou em outro turno)."
            )

    except Exception as e:
        logger.error(f"Erro ao consultar disponibilidade: {e}")
        return "Erro ao consultar agenda."

@tool
async def create_event(date_str: str, time_str: str, patient_name: str, phone: str = "", cpf: str = "", dob: str = "") -> str:
    """
    Cria um agendamento na agenda do Google com validação estrita de dados e idempotência.
    """
    from app.core.validators import validate_cpf, sanitize_text

    # 1. Trava Zero-Trust: Obrigatoriedade de Nome e CPF Válido
    if not patient_name or len(patient_name.strip()) < 3:
        return "Erro de validação: O nome completo do paciente é obrigatório para agendamento. Por favor, solicite o nome completo."

    if not cpf or not validate_cpf(cpf):
        return f"Erro de validação de segurança: O CPF '{cpf or 'não informado'}' é inválido. É obrigatório coletar e validar o CPF oficial do paciente antes de registrar a consulta na agenda médica."

    # 2. Sanitização Estrita de Inputs (Anti-Injection)
    patient_name = sanitize_text(patient_name, max_length=100)
    phone = sanitize_text(phone, max_length=30)
    cpf = sanitize_text(cpf, max_length=20)
    dob = sanitize_text(dob, max_length=20)

    # 3. Persistência no Banco de Dados (Tabela Appointments & Kanban)
    import re
    import uuid
    from app.database import AsyncSessionLocal
    from app.models.chat import Appointment, Contact
    from sqlalchemy.future import select

    try:
        dt_start = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        clean_phone = re.sub(r"\D", "", phone) if phone else ""
        async with AsyncSessionLocal() as session:
            contact_id = None
            if clean_phone:
                stmt = select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
                res = await session.execute(stmt)
                contact = res.scalars().first()
                if contact:
                    contact_id = contact.id
                    contact.stage = "agendado"

            if not contact_id:
                new_contact = Contact(id=str(uuid.uuid4()), phone_number=clean_phone or "0000000000", name=patient_name, stage="agendado")
                session.add(new_contact)
                await session.flush()
                contact_id = new_contact.id

            new_apt = Appointment(
                contact_id=contact_id,
                patient_name=patient_name,
                appointment_time=dt_start,
                status="agendado"
            )
            session.add(new_apt)
            await session.commit()
    except Exception as db_err:
        logger.error(f"Erro ao salvar no banco: {db_err}")

    # 4. Geração do Link Oficial de 1 Clique para a Agenda Pessoal do Google do Paciente (Compacto e Limpo)
    import urllib.parse
    import urllib.request
    google_cal_link = ""
    try:
        dt_local = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        # Horário de Brasília (UTC-3) convertido para UTC (YYYYMMDDTHHMMSSZ)
        dt_utc_start = dt_local + datetime.timedelta(hours=3)
        dt_utc_end = dt_utc_start + datetime.timedelta(hours=1)
        
        dates_param = f"{dt_utc_start.strftime('%Y%m%dT%H%M%SZ')}/{dt_utc_end.strftime('%Y%m%dT%H%M%SZ')}"
        title_param = urllib.parse.quote(f"Consulta Alergia - {patient_name.split()[0] if patient_name else 'Clínica Respirar'}")
        details_param = urllib.parse.quote("Consulta Médica na Clínica Respirar.\nAv. Paulista, 1000 - Cj 1204.")
        location_param = urllib.parse.quote("Av. Paulista, 1000, Bela Vista, São Paulo")
        
        long_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title_param}&dates={dates_param}&details={details_param}&location={location_param}"
        
        # Encurtando o URL (fallback para o URL longo caso falhe)
        try:
            req = urllib.request.Request(f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(long_url)}")
            with urllib.request.urlopen(req, timeout=3) as response:
                google_cal_link = response.read().decode('utf-8')
        except Exception as e_short:
            logger.warning(f"Erro ao encurtar link: {e_short}")
            google_cal_link = long_url

        # NOVO: Gerar arquivo .ics e enviar diretamente como documento via Evolution API
        if clean_phone:
            ics_lines = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//Clinica Respirar//IA Amanda//PT",
                "BEGIN:VEVENT",
                f"DTSTAMP:{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{dt_utc_start.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{dt_utc_end.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:Consulta Alergia - {patient_name.split()[0] if patient_name else 'Respirar'}",
                f"DESCRIPTION:Consulta Médica na Clínica Respirar.\\nAv. Paulista\\, 1000 - Cj 1204.",
                f"LOCATION:Av. Paulista\\, 1000\\, Bela Vista\\, São Paulo",
                "END:VEVENT",
                "END:VCALENDAR"
            ]
            ics_bytes = "\r\n".join(ics_lines).encode("utf-8")
            from app.services.evolution_api import send_document_message
            import asyncio
            asyncio.create_task(
                send_document_message(
                    number=clean_phone,
                    document_bytes=ics_bytes,
                    filename=f"Consulta_{patient_name.split()[0] if patient_name else 'Respirar'}.ics",
                    caption="🗓️ Toque neste arquivo para salvar na sua agenda automaticamente!"
                )
            )

    except Exception as err:
        logger.warning(f"Erro ao gerar link/ICS do Google Calendar: {err}")

    # Retorno limpo e humanizado para a Amanda entregar ao paciente
    link_info = f"\n\nLink do Google Agenda (alternativo):\n{google_cal_link}" if google_cal_link else ""

    service = get_calendar_service()
    if not service:
        return (
            f"Agendamento de {patient_name} confirmado no sistema médico para o dia {date_str} às {time_str}!\n"
            f"INSTRUÇÃO PARA A AMANDA:\n"
            f"1. Confirme a data e o horário com carinho no singular.\n"
            f"2. O arquivo de convite (.ics) já foi enviado automaticamente pelo sistema! Apenas diga: 'Já enviei o arquivo de convite logo abaixo para você salvar na sua agenda com 1 toque!'\n"
            f"3. Pergunte com delicadeza se ele gostaria que você envie o endereço e a localização no mapa / Waze."
        )

    try:
        start_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + datetime.timedelta(hours=1)
        
        desc = f"Telefone: {phone}"
        if cpf:
            desc += f"\nCPF: {cpf}"
        if dob:
            desc += f"\nData de Nascimento: {dob}"

        event = {
            'summary': f'Consulta - {patient_name}',
            'description': desc,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
        }

        import asyncio
        created_event = await asyncio.to_thread(
            service.events().insert(calendarId=CALENDAR_ID, body=event).execute
        )
        event_id = created_event.get("id")

        # Update event ID in DB
        if contact_id:
            async with AsyncSessionLocal() as session:
                # Get the most recent appointment for this contact
                stmt = select(Appointment).where(
                    Appointment.contact_id == contact_id
                ).order_by(Appointment.created_at.desc()).limit(1)
                res = await session.execute(stmt)
                last_apt = res.scalars().first()
                if last_apt:
                    last_apt.google_event_id = event_id
                    await session.commit()
        
        return (
            f"Sucesso! O agendamento de {patient_name} foi registrado no Google Agenda médico para o dia {date_str} às {time_str}. Event ID: {event_id}\n"
            f"INSTRUÇÃO PARA A AMANDA:\n"
            f"1. Confirme a data e o horário com entusiasmo (apenas 1 frase, no singular, acolhedora).\n"
            f"2. O arquivo de convite (.ics) já foi disparado! Apenas avise: 'Já enviei o convite logo abaixo para você salvar na sua agenda do celular com 1 clique!'\n"
            f"3. Pergunte gentilmente se o paciente deseja o endereço da clínica / link do Waze."
        )

    except Exception as e:
        logger.error(f"Erro ao criar evento na API do Google: {e}")
        return (
            f"Aviso técnico (INVISÍVEL PRO PACIENTE): Ocorreu um erro interno na API do Google Calendar ({str(e)}), mas o agendamento no banco de dados foi criado! "
            f"Aja como se tivesse dado certo perfeitamente e siga o fluxo: \n"
            f"1. Confirme {date_str} às {time_str}.\n"
            f"2. Informe que o convite foi enviado abaixo.\n"
            f"3. Ofereça a localização."
        )

@tool
async def cancel_event(phone: str) -> str:
    """Cancela o agendamento mais recente do paciente, liberando a vaga."""
    import re
    from app.database import AsyncSessionLocal
    from app.models.chat import Appointment, Contact
    from sqlalchemy.future import select

    clean_phone = re.sub(r"\D", "", phone) if phone else ""
    if not clean_phone:
        return "Erro: Telefone não fornecido para cancelamento."

    async with AsyncSessionLocal() as session:
        # Pega o contato
        stmt = select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
        res = await session.execute(stmt)
        contact = res.scalars().first()

        if not contact:
            return "Não encontrei nenhum paciente cadastrado com esse telefone para cancelar."

        # Pega o agendamento ativo mais recente
        stmt_apt = select(Appointment).where(
            Appointment.contact_id == contact.id,
            Appointment.status.in_(["agendado", "confirmado"])
        ).order_by(Appointment.created_at.desc()).limit(1)
        res_apt = await session.execute(stmt_apt)
        apt = res_apt.scalars().first()

        if not apt:
            return "Não encontrei nenhum agendamento ativo para cancelar."

        # Cancela no banco
        apt.status = "cancelado"
        contact.stage = "novo_contato"
        await session.commit()

        # Cancela no Google
        if apt.google_event_id:
            service = get_calendar_service()
            if service:
                import asyncio
                try:
                    await asyncio.to_thread(
                        service.events().delete(calendarId=CALENDAR_ID, eventId=apt.google_event_id).execute
                    )
                except Exception as e:
                    logger.error(f"Erro ao deletar evento no google: {e}")
        
        return "Cancelamento efetuado com sucesso. INSTRUÇÃO PARA AMANDA: Acolha o paciente, confirme o cancelamento de forma gentil e deixe as portas abertas para quando ele quiser remarcar."

@tool
async def reschedule_event(phone: str, new_date_str: str, new_time_str: str) -> str:
    """Remarca o agendamento mais recente do paciente para a nova data (YYYY-MM-DD) e hora (HH:MM)."""
    import re
    from app.database import AsyncSessionLocal
    from app.models.chat import Appointment, Contact
    from sqlalchemy.future import select

    clean_phone = re.sub(r"\D", "", phone) if phone else ""
    if not clean_phone:
        return "Erro: Telefone não fornecido para reagendamento."

    async with AsyncSessionLocal() as session:
        stmt = select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
        res = await session.execute(stmt)
        contact = res.scalars().first()

        if not contact:
            return "Não encontrei cadastro com esse telefone."

        stmt_apt = select(Appointment).where(
            Appointment.contact_id == contact.id,
            Appointment.status.in_(["agendado", "confirmado"])
        ).order_by(Appointment.created_at.desc()).limit(1)
        res_apt = await session.execute(stmt_apt)
        apt = res_apt.scalars().first()

        if not apt:
            return "Não encontrei nenhum agendamento ativo para remarcar."

        if apt.reschedule_count >= 2:
            return "ERRO: O limite de 2 reagendamentos foi atingido para essa consulta. INSTRUÇÃO PARA AMANDA: Informe ao paciente gentilmente que o sistema não permite mais reagendamentos automáticos e oriente a falar com a ouvidoria/gerência."

        # Verifica conflito no Google Calendar para o novo horário
        service = get_calendar_service()
        if service:
            start_time = f"{new_date_str}T00:00:00-03:00"
            end_time = f"{new_date_str}T23:59:59-03:00"
            import asyncio
            try:
                events_result = await asyncio.to_thread(
                    service.events().list(calendarId=CALENDAR_ID, timeMin=start_time, timeMax=end_time, singleEvents=True).execute
                )
                events = events_result.get('items', [])
                dt_new_start = datetime.datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
                dt_new_end = dt_new_start + datetime.timedelta(hours=1)
                
                conflito = False
                for event in events:
                    if event.get("id") == apt.google_event_id: continue # ignora o evento atual
                    s = event['start'].get('dateTime')
                    e = event['end'].get('dateTime')
                    if s and e:
                        try:
                            s_dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
                            e_dt = datetime.datetime.fromisoformat(e.replace("Z", "+00:00"))
                            if dt_new_start < e_dt and dt_new_end > s_dt:
                                conflito = True
                        except: pass
                if conflito:
                    return f"O horário {new_date_str} às {new_time_str} já está ocupado. Por favor, ofereça outro horário usando a ferramenta check_availability."
            except Exception as e:
                logger.error(f"Erro ao checar conflitos no reagendamento: {e}")

        # Atualiza o banco
        dt_start = datetime.datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M")
        apt.appointment_time = dt_start
        apt.reschedule_count += 1
        await session.commit()

        # Atualiza no Google
        if apt.google_event_id and service:
            try:
                event = await asyncio.to_thread(service.events().get(calendarId=CALENDAR_ID, eventId=apt.google_event_id).execute)
                event['start'] = {'dateTime': dt_start.isoformat(), 'timeZone': 'America/Sao_Paulo'}
                event['end'] = {'dateTime': (dt_start + datetime.timedelta(hours=1)).isoformat(), 'timeZone': 'America/Sao_Paulo'}
                await asyncio.to_thread(service.events().update(calendarId=CALENDAR_ID, eventId=apt.google_event_id, body=event).execute)
            except Exception as e:
                logger.error(f"Erro ao atualizar google calendar: {e}")

@tool
async def confirm_event(phone: str) -> str:
    """Confirma o agendamento mais recente do paciente (altera o status para 'confirmado' no banco de dados)."""
    import re
    from app.database import AsyncSessionLocal
    from app.models.chat import Appointment, Contact
    from sqlalchemy.future import select

    clean_phone = re.sub(r"\D", "", phone) if phone else ""
    if not clean_phone:
        return "Erro: Telefone não fornecido para confirmação."

    async with AsyncSessionLocal() as session:
        stmt = select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
        res = await session.execute(stmt)
        contact = res.scalars().first()

        if not contact:
            return "Não encontrei cadastro com esse telefone."

        stmt_apt = select(Appointment).where(
            Appointment.contact_id == contact.id,
            Appointment.status == "agendado"
        ).order_by(Appointment.created_at.desc()).limit(1)
        res_apt = await session.execute(stmt_apt)
        apt = res_apt.scalars().first()

        if not apt:
            return "Não encontrei nenhum agendamento pendente de confirmação."

        apt.status = "confirmado"
        await session.commit()
        return "Sucesso! O agendamento foi confirmado no sistema. INSTRUÇÃO PARA AMANDA: Agradeça ao paciente pela confirmação e reforce que a clínica o aguarda no horário marcado."
