import os
import datetime
import json
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
        # Define início e fim do dia (America/Sao_Paulo timezone -3)
        # Formato ISO correto para API do Google Calendar: 2026-08-27T00:00:00-03:00
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
        
        # Grade de horários de trabalho (1 hora cada)
        horarios_trabalho = [
            "09:00", "10:00", "11:00", 
            # Almoço 12:00 as 14:00
            "14:00", "15:00", "16:00", "17:00"
        ]
        
        ocupados = []
        for event in events:
            # Pegamos o horário de início do evento
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
                # O formato retorna algo como 2026-08-27T09:00:00-03:00
                hora = start.split('T')[1][:5]
                ocupados.append(hora)
        
        livres = [h for h in horarios_trabalho if h not in ocupados]
        
        if livres:
            return f"Horários livres para {date_str}: " + ", ".join(livres)
        else:
            return f"Não há horários disponíveis para {date_str}."

    except Exception as e:
        logger.error(f"Erro ao consultar disponibilidade: {e}")
        return "Erro ao consultar agenda."

@tool
def create_event(date_str: str, time_str: str, patient_name: str, phone: str = "") -> str:
    """
    Cria um agendamento na agenda do Google.
    """
    service = get_calendar_service()
    if not service:
        return f"Agendamento de {patient_name} confirmado para {date_str} às {time_str} (Modo Simulação)"

    try:
        # Criando datetime de inicio e fim (duração de 1 hora)
        start_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + datetime.timedelta(hours=1)

        event = {
            'summary': f'Consulta - {patient_name}',
            'description': f'Telefone: {phone}',
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
        
        # Atualizar a fase do Kanban para agendado!
        if phone:
            from app.database import async_session_maker
            from app.models.chat import Contact
            from sqlalchemy.future import select
            import asyncio
            
            async def update_stage():
                async with async_session_maker() as session:
                    # O JID geralmente vem como DDI+DDD+numero@s.whatsapp.net. 
                    # Como o 'phone' pode ser só o número ou o JID, procuramos com 'like' ou exato.
                    stmt = select(Contact).where(Contact.phone_number.contains(phone))
                    result = await session.execute(stmt)
                    contact = result.scalar_one_or_none()
                    if contact:
                        contact.stage = "agendado"
                        await session.commit()
                        
            # Roda a função de forma fire-and-forget
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(update_stage())
            except RuntimeError:
                asyncio.run(update_stage())

        return f"Agendamento confirmado no Google Calendar! Link: {created_event.get('htmlLink')}"

    except Exception as e:
        logger.error(f"Erro ao criar evento: {e}")
        return "Falha ao criar o agendamento no sistema."
