import re
from collections.abc import Sequence

from app.core.validators import validate_cpf

CPF_CANDIDATE_PATTERN = re.compile(r"(?<!\d)(?:\d[ .-]?){10}\d(?!\d)")
DATE_PATTERN = re.compile(r"(?<!\d)(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})(?!\d)")


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
