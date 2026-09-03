"""Canonical clinic location used by reminders, calendar events and assistants."""

CLINIC_NAME = "Clínica Respirar"
CLINIC_ROOM = "sala 3021"
CLINIC_ADDRESS = "Connect Towers, sala 3021 - QS 01, Rua 212, Lotes 19, 21 e 23 - Taguatinga Sul, Brasília - DF"
CLINIC_GOOGLE_MAPS_URL = "https://maps.app.goo.gl/search/Connect+Towers+Taguatinga"
CLINIC_WAZE_URL = "https://ul.waze.com/ul?ll=-15.84028486%2C-48.04482222&navigate=yes&zoom=17&utm_campaign=default&utm_source=waze_website&utm_medium=lm_share_location"


def clinic_location_text() -> str:
    return f"{CLINIC_ADDRESS}\nWaze: {CLINIC_WAZE_URL}"
