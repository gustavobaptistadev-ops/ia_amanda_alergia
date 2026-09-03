import os
import urllib.parse


def create_calendar_link(appointment_id: str) -> str:
    """Create a short opaque link based on the appointment UUID."""
    public_api_url = os.getenv("PUBLIC_API_URL", "").rstrip("/")
    return f"{public_api_url}/api/v1/calendar/p/{appointment_id}" if public_api_url else ""


def build_google_calendar_url(date_str: str, time_str: str, patient_name: str, address: str) -> str:
    import datetime

    dt_local = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    dt_utc_start = dt_local + datetime.timedelta(hours=3)
    dt_utc_end = dt_utc_start + datetime.timedelta(hours=1)
    dates = f"{dt_utc_start:%Y%m%dT%H%M%SZ}/{dt_utc_end:%Y%m%dT%H%M%SZ}"
    title = urllib.parse.quote(f"Consulta Alergia - {patient_name.split()[0] if patient_name else 'Clínica Lifeline One'}")
    details = urllib.parse.quote(f"Consulta Médica na Clínica Lifeline One.\n{address}")
    location = urllib.parse.quote(address)
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={dates}&details={details}&location={location}"
