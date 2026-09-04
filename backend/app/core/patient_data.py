import re
import unicodedata
from collections.abc import Sequence

from app.core.validators import validate_cpf

CPF_CANDIDATE_PATTERN = re.compile(r"(?<!\d)(?:\d[ .-]?){10}\d(?!\d)")
DATE_PATTERN = re.compile(r"(?<!\d)(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})(?!\d)")
COMPLAINT_TERMS = (
    "alergia", "coceira", "coçar", "mancha", "vermelhidão", "vermelhidao",
    "rinite", "sinusite", "asma", "tosse", "espirro", "falta de ar",
    "pele", "urticária", "urticaria", "inchaço", "inchaco", "reação",
    "reacao", "sintoma", "sintomas", "dor", "queixa", "problema de saúde",
    "problema de saude", "estou com", "estou sentindo", "sinto",
)

INSURANCE_OPERATORS = (
    "amil", "unimed", "bradesco", "sulamerica", "sul america", "assefaz",
    "ipsemg", "geap", "cassi", "notredame", "hapvida", "amil",
)

MEDICATION_TERMS = (
    "antialergico", "antialérgico", "corticoide", "corticóide", "alegra", "allegra",
    "polaramine", "loratadina", "desloratadina", "fexofenadina", "cetirizina",
    "prednisona", "prednisolona", "dexametasona", "betametasona", "remedio", "remédio",
    "pomada", "creme", "xarope", "bombinha", "aerolin", "clenil", "flixotide",
    "seretide", "alenia", "symbicort", "foster",
)

DURATION_TERMS = (
    "dia", "dias", "semana", "semanas", "mes", "meses", "mês", "ano", "anos",
    "desde", "tempo", "hoje", "ontem", "anteontem", "agora", "horas"
)



def extract_cpf_from_text(text: str) -> str | None:
    """Extract a valid CPF as text, preserving leading zeros."""
    if not text:
        return None
    for candidate in CPF_CANDIDATE_PATTERN.findall(text):
        digits = re.sub(r"\D", "", candidate)
        if len(digits) == 11 and validate_cpf(digits):
            return digits
    return None


def extract_latest_cpf(messages: Sequence) -> str | None:
    """Find the newest valid CPF only in patient messages."""
    for message in reversed(messages or []):
        if getattr(message, "type", None) != "human":
            continue
        cpf = extract_cpf_from_text(getattr(message, "content", ""))
        if cpf:
            return cpf
    return None


def contains_date(text: str) -> bool:
    """Detect a date supplied by the patient without converting it to a number."""
    return bool(text and DATE_PATTERN.search(text))


def extract_latest_date(messages: Sequence) -> str | None:
    """Return the newest date supplied by the patient, preserving its format."""
    for message in reversed(messages or []):
        if getattr(message, "type", None) != "human":
            continue
        match = DATE_PATTERN.search(getattr(message, "content", "") or "")
        if match:
            return match.group(0)
    return None

EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")

def extract_email(text: str) -> str | None:
    if not text:
        return None
    match = EMAIL_PATTERN.search(text)
    if match:
        return match.group(1).lower()
    return None


def extract_payment_type(messages: Sequence) -> str | None:
    """Detect an explicit private/insurance choice made by the patient."""
    for message in reversed(messages or []):
        if getattr(message, "type", None) != "human":
            continue
        raw_text = (getattr(message, "content", "") or "").lower()
        text = unicodedata.normalize("NFKD", raw_text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = re.sub(r"\s+", " ", text).strip()
        if re.search(r"\b(particular|vou pagar particular|sem convenio|sem plano)\b", text):
            return "particular"
        if any(operator in text for operator in INSURANCE_OPERATORS):
            return "convenio"
        if re.search(r"\b(meu convenio|tenho convenio|pelo convenio|por convenio|meu plano|plano de saude)\b", text):
            return "convenio"
    return None


def has_patient_complaint(messages: Sequence) -> bool:
    """Return True when the patient described a health complaint in the conversation."""
    for message in messages or []:
        if getattr(message, "type", None) != "human":
            continue
        text = getattr(message, "content", "") or ""
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        if any(term in normalized for term in COMPLAINT_TERMS):
            return True
    return False


def extract_medications(messages: Sequence) -> list[str]:
    """Return a list of medication keywords mentioned by the patient."""
    meds = set()
    for message in messages or []:
        if getattr(message, "type", None) != "human":
            continue
        text = getattr(message, "content", "") or ""
        normalized = unicodedata.normalize("NFKD", text.lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        
        for term in MEDICATION_TERMS:
            norm_term = unicodedata.normalize("NFKD", term.lower())
            norm_term = "".join(char for char in norm_term if not unicodedata.combining(char))
            if re.search(r"\b" + re.escape(norm_term) + r"\b", normalized):
                meds.add(term)
    return list(meds)


def has_symptom_duration(messages: Sequence) -> bool:
    """Return True if the patient mentions temporal words usually indicating duration."""
    for message in messages or []:
        if getattr(message, "type", None) != "human":
            continue
        text = getattr(message, "content", "") or ""
        normalized = unicodedata.normalize("NFKD", text.lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        
        for term in DURATION_TERMS:
            norm_term = unicodedata.normalize("NFKD", term.lower())
            norm_term = "".join(char for char in norm_term if not unicodedata.combining(char))
            if re.search(r"\b" + re.escape(norm_term) + r"\b", normalized):
                return True
    return False

def extract_clinical_summary(messages: Sequence) -> str:
    """Return a concatenated string of the patient's messages that contain medical terms."""
    summary = []
    for message in messages or []:
        if getattr(message, "type", None) != "human":
            continue
        text = getattr(message, "content", "") or ""
        normalized = unicodedata.normalize("NFKD", text.lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        
        has_term = False
        for term in COMPLAINT_TERMS + DURATION_TERMS + MEDICATION_TERMS:
            norm_term = unicodedata.normalize("NFKD", term.lower())
            norm_term = "".join(char for char in norm_term if not unicodedata.combining(char))
            if re.search(r"\b" + re.escape(norm_term) + r"\b", normalized):
                has_term = True
                break
        
        if has_term:
            summary.append(text.strip())
            
    return " | ".join(summary) if summary else ""
