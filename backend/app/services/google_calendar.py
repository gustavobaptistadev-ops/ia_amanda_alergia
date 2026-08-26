import os
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
# O arquivo credentials.json deverá ser salvo na pasta backend/
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '../../credentials.json')

# O ID da agenda (pode ser "primary" se for a conta dona, mas como é Service Account, precisamos do e-mail da agenda)
# O usuário precisará compartilhar a agenda com o e-mail do Service Account.
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

def get_calendar_service():
    """Autentica e retorna o serviço da API do Google Calendar."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.warning("Arquivo credentials.json não encontrado. Integração com Google Calendar desativada.")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Erro ao inicializar Google Calendar: {e}")
        return None

def check_availability(date_str: str) -> str:
    """
    Checa a disponibilidade na agenda para uma data específica (YYYY-MM-DD).
    """
    service = get_calendar_service()
    if not service:
        # Se não tiver configurado ainda, retorna uma resposta mock para desenvolvimento
        return f"Os seguintes horários estão livres para o dia {date_str}: 09:00, 10:30, 14:00 e 15:30. (Modo Simulação)"

    try:
        # Define início e fim do dia para a busca
        start_time = datetime.datetime.strptime(date_str, "%Y-%m-%d").isoformat() + 'T00:00:00Z'
        end_time = datetime.datetime.strptime(date_str, "%Y-%m-%d").isoformat() + 'T23:59:59Z'

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Lógica simplificada: se tem poucos eventos, assumimos horários livres
        # No mundo real, faríamos a subtração dos horários ocupados contra a grade de trabalho.
        horarios_trabalho = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]
        ocupados = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
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
        return f"Agendamento confirmado no Google Calendar! Link: {created_event.get('htmlLink')}"

    except Exception as e:
        logger.error(f"Erro ao criar evento: {e}")
        return "Falha ao criar o agendamento no sistema."
