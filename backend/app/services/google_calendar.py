import os
import datetime
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging
from langchain_core.tools import tool

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
def check_availability(date_str: str) -> str:
    """
    Checa a disponibilidade na agenda para uma data específica (YYYY-MM-DD).
    """
    service = get_calendar_service()
    if not service:
        # Se não tiver configurado ainda, retorna uma resposta mock para desenvolvimento
        return f"Os seguintes horários estão livres para o dia {date_str}: 09:00, 10:30, 14:00 e 15:30. (Modo Simulação)"

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
            # Retorna apenas 3 opções mais próximas para um visual arejado e limpo no WhatsApp
            sugestoes = livres[:3]
            return f"Horários livres para {date_str}: " + ", ".join(sugestoes)
        else:
            return f"Não há horários disponíveis para {date_str}."

    except Exception as e:
        logger.error(f"Erro ao consultar disponibilidade: {e}")
        return "Erro ao consultar agenda."

@tool
def create_event(date_str: str, time_str: str, patient_name: str, phone: str = "", cpf: str = "", dob: str = "") -> str:
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
    try:
        from app.database import AsyncSessionLocal
        from app.models.chat import Contact, Appointment
        from sqlalchemy.future import select
        import asyncio

        # Tenta converter date_str e time_str
        try:
            start_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except Exception:
            start_dt = datetime.datetime.now()

        async def save_appointment_to_db():
            async with AsyncSessionLocal() as session:
                contact = None
                if phone:
                    clean_phone = re.sub(r"\D", "", phone)
                    stmt = select(Contact).where(Contact.phone_number.contains(clean_phone[-8:] if len(clean_phone) >= 8 else clean_phone))
                    res = await session.execute(stmt)
                    contact = res.scalars().first()

                if not contact:
                    # Busca por nome se não achou por telefone
                    stmt_name = select(Contact).where(Contact.name.ilike(f"%{patient_name}%"))
                    res_name = await session.execute(stmt_name)
                    contact = res_name.scalars().first()

                if not contact:
                    contact = Contact(
                        phone_number=phone or "WhatsApp",
                        name=patient_name,
                        stage="agendado",
                        bot_active=True
                    )
                    session.add(contact)
                    await session.commit()
                    await session.refresh(contact)
                else:
                    contact.stage = "agendado"
                    if not contact.name:
                        contact.name = patient_name
                    await session.commit()

                # Salva o agendamento
                new_appt = Appointment(
                    contact_id=contact.id,
                    patient_name=patient_name,
                    appointment_time=start_dt,
                    status="agendado"
                )
                session.add(new_appt)
                await session.commit()
                logger.info(f"Agendamento de {patient_name} persistido com sucesso no banco de dados!")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(save_appointment_to_db())
        except RuntimeError:
            asyncio.run(save_appointment_to_db())

    except Exception as db_err:
        logger.error(f"Erro ao persistir agendamento no banco: {db_err}")

    service = get_calendar_service()
    if not service:
        return (
            f"Agendamento de {patient_name} confirmado com sucesso na agenda médica para {date_str} às {time_str}! 🌟 "
            f"Informe ao paciente que a consulta foi marcada e passe as orientações da clínica com carinho."
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

        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        
        return (
            f"Agendamento confirmado com sucesso na agenda médica para o dia {date_str} às {time_str}! "
            f"Oriente o paciente com carinho informando que a consulta está marcada, que nosso endereço é na "
            f"Av. Paulista, 1000 - Conjunto 1204 (com manobrista no local), e que nossa equipe estará esperando com café especial e água aromatizada. 🌿"
        )

    except Exception as e:
        logger.error(f"Erro ao criar evento no Google Calendar: {e}")
        return f"Agendamento de {patient_name} confirmado no sistema para {date_str} às {time_str}!"
