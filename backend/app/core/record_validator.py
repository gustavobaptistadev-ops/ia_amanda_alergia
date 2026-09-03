"""Validação administrativa do prontuário antes de qualquer operação de agenda.

Este módulo não diagnostica, não decide conduta clínica e não substitui a equipe.
Sua responsabilidade é verificar consistência dos dados fornecidos pelo contato.
"""

import datetime as dt
import re
import unicodedata
from collections.abc import Sequence
from typing import Any

from app.core.patient_data import extract_payment_type
from app.core.validators import validate_cpf


_DATE_PATTERN = re.compile(r"(?<!\d)(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})(?!\d)")
_CPF_PATTERN = re.compile(r"(?<!\d)(?:\d[ .-]?){10}\d(?!\d)")
_NAME_BLOCKLIST = {
    "eu", "meu", "minha", "nome", "cpf", "nascimento", "consulta", "agendar",
    "marcar", "alergia", "coceira", "dor", "estou", "sinto", "quero",
    "plano", "bradesco", "amil", "unimed", "particular", "convenio", "saude",
}


def _patient_messages(messages: Sequence[Any]) -> list[str]:
    return [
        str(getattr(message, "content", "") or "").strip()
        for message in messages or []
        if getattr(message, "type", None) == "human"
    ]


def _parse_date(value: str) -> dt.date | None:
    try:
        if "/" in value:
            return dt.datetime.strptime(value, "%d/%m/%Y").date()
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _extract_dates(messages: Sequence[Any]) -> list[str]:
    dates: list[str] = []
    for text in _patient_messages(messages):
        dates.extend(match.group(1) for match in _DATE_PATTERN.finditer(text))
    return dates


def _extract_cpfs(messages: Sequence[Any]) -> list[str]:
    cpfs: list[str] = []
    for text in _patient_messages(messages):
        for candidate in _CPF_PATTERN.findall(text):
            digits = re.sub(r"\D", "", candidate)
            if len(digits) == 11:
                cpfs.append(digits)
    return cpfs


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" .,!?\n\r\t")).strip()


def _looks_like_name(value: str | None) -> bool:
    if not value:
        return False
    words = _normalize_name(value).split()
    normalized = unicodedata.normalize("NFKD", value.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return (
        2 <= len(words) <= 8
        and all(re.fullmatch(r"[A-Za-zÀ-ÿ'-]+", word) for word in words)
        and not any(word in _NAME_BLOCKLIST for word in normalized.split())
    )


def _extract_name(messages: Sequence[Any], entities: dict[str, Any]) -> str | None:
    routed_name = entities.get("name")
    if _looks_like_name(routed_name):
        return _normalize_name(routed_name)

    message_list = list(messages or [])
    for index in range(len(message_list) - 1, -1, -1):
        message = message_list[index]
        if getattr(message, "type", None) != "human":
            continue
        text = str(getattr(message, "content", "") or "").strip()
        match = re.search(
            r"\b(?:meu nome(?: completo)? e|me chamo|sou)\s+(.+?)(?:\s+cpf\b|\s+nascimento\b|$)",
            _remove_accents(text),
            re.IGNORECASE,
        )
        if match and _looks_like_name(match.group(1)):
            return _normalize_name(match.group(1))

        previous = message_list[index - 1] if index else None
        previous_text = _remove_accents(str(getattr(previous, "content", "") or "")).lower()
        if "nome completo" in previous_text and _looks_like_name(text):
            return _normalize_name(text)

    # Permite respostas compostas ou fluxos sem a mensagem intermediária da Amanda.
    for text in reversed(_patient_messages(messages)):
        if _looks_like_name(text):
            return _normalize_name(text)
    return None


def _remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if not unicodedata.combining(char))


def validate_patient_record(
    messages: Sequence[Any],
    routing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Retorna uma decisão estruturada para o orquestrador.

    Dados sensíveis são usados somente em memória nesta função e não são incluídos
    no resultado de logs. A decisão nunca deve ser tomada diretamente pela LLM.
    """
    routing = routing or {}
    entities = routing.get("entities", {})
    cpfs = _extract_cpfs(messages)
    dates = _extract_dates(messages)
    name = _extract_name(messages, entities)
    payment_type = entities.get("payment_type") or extract_payment_type(messages)
    third_party = bool(entities.get("third_party"))
    conflicts: list[str] = []
    invalid_fields: list[str] = []

    if len(set(cpfs)) > 1:
        conflicts.append("multiple_cpf_values")
    if len(set(dates)) > 1:
        parsed_dates = [_parse_date(value) for value in dates]
        if len({value for value in parsed_dates if value is not None}) > 1:
            conflicts.append("multiple_birth_dates")

    cpf = cpfs[-1] if cpfs else None
    if cpf and not validate_cpf(cpf):
        invalid_fields.append("cpf")

    birth_date = dates[-1] if dates else None
    parsed_birth_date = _parse_date(birth_date) if birth_date else None
    today = dt.date.today()
    if birth_date and parsed_birth_date is None:
        invalid_fields.append("birth_date")
    elif parsed_birth_date and (parsed_birth_date > today or parsed_birth_date < today.replace(year=today.year - 120)):
        invalid_fields.append("birth_date")

    if not name:
        missing_fields = ["name"]
    elif "cpf" in invalid_fields:
        missing_fields = ["cpf"]
    elif not cpf:
        missing_fields = ["cpf"]
    elif "birth_date" in invalid_fields:
        missing_fields = ["birth_date"]
    elif not birth_date:
        missing_fields = ["birth_date"]
    elif not payment_type:
        missing_fields = ["payment_type"]
    else:
        missing_fields = []

    if conflicts:
        next_action = "REVIEW_PATIENT_DATA"
    elif missing_fields:
        next_action = {
            "name": "COLLECT_NAME",
            "cpf": "COLLECT_CPF",
            "birth_date": "COLLECT_BIRTH_DATE",
            "payment_type": "COLLECT_PAYMENT_TYPE",
        }[missing_fields[0]]
    else:
        next_action = routing.get("next_action") if routing.get("next_action") == "CONFIRM_SLOT" else "CHECK_AVAILABILITY"

    valid = not conflicts and not invalid_fields and not missing_fields
    return {
        "valid": valid,
        "confidence": 1.0 if valid or conflicts or invalid_fields else 0.98,
        "patient_type": "third_party" if third_party else "self",
        "fields_confirmed": [
            field for field, value in {
                "name": name,
                "cpf": cpf,
                "birth_date": parsed_birth_date,
                "payment_type": payment_type,
            }.items() if value and field not in invalid_fields
        ],
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "conflicts": conflicts,
        "next_action": next_action,
        "human_review_required": bool(conflicts),
    }
