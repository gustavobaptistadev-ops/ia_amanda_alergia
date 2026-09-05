import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def mock_check_availability(date_str: str = None) -> list[str]:
    """Mock API para verificar horários disponíveis na agenda."""
    # Retorna horários fictícios para amanhã
    amanha = datetime.now() + timedelta(days=1)
    dia_fmt = amanha.strftime("%d/%m/%Y")

    return [f"{dia_fmt} às 09:00", f"{dia_fmt} às 14:30", f"{dia_fmt} às 16:00"]


def mock_schedule_appointment(
    patient_name: str, patient_cpf: str, date_time: str
) -> bool:
    """Mock API para confirmar um agendamento."""
    logger.info(
        f"Agendamento confirmado no sistema externo para: {patient_name} (CPF: {patient_cpf}) no dia/hora: {date_time}"
    )
    return True
