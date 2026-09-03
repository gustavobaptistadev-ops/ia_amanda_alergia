"""Roteamento determinístico de conversas antes da atuação da LLM."""

import re
import unicodedata
import datetime
from collections.abc import Sequence
from typing import Any

from app.core.patient_data import (
    contains_date,
    extract_latest_cpf,
    extract_payment_type,
    has_patient_complaint,
)


def normalize_text(text: str) -> str:
    """Normaliza acentos e espaços para permitir regras previsíveis."""
    normalized = unicodedata.normalize("NFKD", text or "")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", normalized.lower()).strip()


THIRD_PARTY_TERMS = (
    "meu filho", "minha filha", "meu pai", "minha mae", "minha mãe",
    "meu marido", "minha esposa", "meu esposo", "minha irma", "meu irmao",
    "minha irmã", "meu irmão", "meu avo", "minha avo", "meu avô", "minha avó",
    "meu dependente", "minha dependente", "outra pessoa", "para ele", "para ela",
    "para meu", "para minha", "responsavel pelo paciente", "responsável pelo paciente",
)

INTENT_TERMS = {
    "FRUSTRACAO_HANDOFF": ("humano", "atendente", "pessoa", "falar com alguém", "falar com alguem"),
    "URGENCIA": ("urgencia", "emergencia", "falta de ar", "sufocando", "anafilaxia", "pronto socorro"),
    "REAGENDAMENTO": ("remarcar", "reagendar", "mudar o dia", "mudar a hora", "mudar a data"),
    "CANCELAMENTO": ("cancelar", "desmarcar"),
    "AGENDAMENTO": ("agendar", "marcar consulta", "marcar horario", "vaga", "consulta"),
}

WEEKDAYS = {
    "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3,
    "sexta": 4, "sabado": 5, "domingo": 6,
}


def _extract_name(text: str) -> str | None:
    """Extrai somente nomes explicitamente apresentados pelo paciente."""
    match = re.search(
        r"\b(?:meu nome(?: completo)? é|me chamo|sou)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){1,5})",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip(" .,!?") if match else None


def route_message(text: str, messages: Sequence[Any] | None = None) -> dict[str, Any]:
    """Classifica uma mensagem e informa a próxima etapa sem chamar a LLM."""
    normalized = normalize_text(text)
    history = list(messages or [])
    human_history = [
        normalize_text(getattr(message, "content", ""))
        for message in history
        if getattr(message, "type", None) == "human"
    ]
    all_patient_text = " ".join(human_history + [normalized])
    is_third_party = any(term in all_patient_text for term in THIRD_PARTY_TERMS)

    for intent, terms in INTENT_TERMS.items():
        if any(term in normalized for term in terms):
            confidence = 0.97 if intent in {"URGENCIA", "CANCELAMENTO", "REAGENDAMENTO"} else 0.94
            break
    else:
        # Respostas curtas continuam no agendamento quando o histórico mostra
        # que a Amanda estava coletando dados cadastrais.
        registration_context = _has_registration_context(history)
        intent = "AGENDAMENTO" if registration_context else "DUVIDA"
        confidence = 0.93 if registration_context else 0.45

    if intent == "AGENDAMENTO":
        missing_fields = []
        if not has_patient_complaint(history + [_Message(text)]):
            next_action = "COLLECT_COMPLAINT"
            confidence = min(confidence, 0.92)
        else:
            if not _extract_name_from_history(history + [_Message(text)]):
                missing_fields.append("name")
            if not extract_latest_cpf(history + [_Message(text)]):
                missing_fields.append("cpf")
            if not any(contains_date(getattr(message, "content", "")) for message in history + [_Message(text)] if getattr(message, "type", None) == "human"):
                missing_fields.append("birth_date")
            if not extract_payment_type(history + [_Message(text)]):
                missing_fields.append("payment_type")
            next_action = {
                "name": "COLLECT_NAME",
                "cpf": "COLLECT_CPF",
                "birth_date": "COLLECT_BIRTH_DATE",
                "payment_type": "COLLECT_PAYMENT_TYPE",
            }.get(missing_fields[0], "CHECK_AVAILABILITY") if missing_fields else (
                "CONFIRM_SLOT" if _extract_preferred_slot(text, history) else "CHECK_AVAILABILITY"
            )
    elif intent in {"CANCELAMENTO", "REAGENDAMENTO"}:
        missing_fields = ["appointment"]
        next_action = "VALIDATE_EXISTING_APPOINTMENT"
    else:
        missing_fields = []
        next_action = "ANSWER_WITH_KNOWLEDGE_BASE" if intent == "DUVIDA" else intent

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "entities": {
            "name": _extract_name_from_history(history + [_Message(text)]),
            "cpf": extract_latest_cpf([_Message(text)]),
            "birth_date": text if contains_date(text) else None,
            "third_party": is_third_party,
            "payment_type": extract_payment_type(history + [_Message(text)]),
            "preferred_slot": _extract_preferred_slot(text, history),
        },
        "missing_fields": missing_fields,
        "next_action": next_action,
    }


def _extract_preferred_slot(text: str, messages: Sequence[Any]) -> dict[str, str] | None:
    """Extract a day/time choice only after availability was presented."""
    normalized = normalize_text(text)
    time_match = re.search(r"\b(?:as|a|pelas?)\s*(\d{1,2})(?::(\d{2}))?\s*h?\b", normalized)
    if not time_match:
        return None

    weekday = next(
        (day for day in WEEKDAYS if re.search(rf"\b{day}(?:-feira)?\b", normalized)),
        None,
    )
    if weekday is None:
        return None

    offered_text = " ".join(
        normalize_text(getattr(message, "content", ""))
        for message in messages or []
        if getattr(message, "type", None) == "ai"
    )
    if not any(marker in offered_text for marker in ("horarios disponiveis", "horarios livres", "horarios")):
        return None

    offered_match = re.search(rf"{weekday}(?:-feira)?[^\d]{{0,30}}(\d{{1,2}})/(\d{{1,2}})", offered_text)
    if offered_match:
        year = datetime.date.today().year
        date_str = f"{year:04d}-{int(offered_match.group(2)):02d}-{int(offered_match.group(1)):02d}"
    else:
        today = datetime.date.today()
        days_ahead = (WEEKDAYS[weekday] - today.weekday()) % 7 or 7
        date_str = (today + datetime.timedelta(days=days_ahead)).isoformat()

    return {
        "date": date_str,
        "time": f"{int(time_match.group(1)):02d}:{time_match.group(2) or '00'}",
    }


def _extract_name_from_history(messages: Sequence[Any]) -> str | None:
    message_list = list(messages or [])
    for index in range(len(message_list) - 1, -1, -1):
        message = message_list[index]
        if getattr(message, "type", None) == "human":
            content = _clean_patient_text(getattr(message, "content", ""))
            name = _extract_name(content)
            if name:
                return name
            previous_message = message_list[index - 1] if index > 0 else None
            asked_for_name = (
                getattr(previous_message, "type", None) == "ai"
                and "nome completo" in normalize_text(
                    getattr(previous_message, "content", "")
                )
            )
            if (index == len(message_list) - 1 or asked_for_name) and _looks_like_standalone_name(content):
                return content.strip(" .,!?")
    return None


def _clean_patient_text(text: str) -> str:
    """Remove o envelope interno antes de aplicar regras de linguagem."""
    cleaned = str(text or "").strip()
    if cleaned.startswith("<user_message>") and cleaned.endswith("</user_message>"):
        cleaned = cleaned[len("<user_message>"):-len("</user_message>")]
    return cleaned.strip()


def _looks_like_standalone_name(text: str) -> bool:
    """Reconhece nome enviado como resposta curta à pergunta de cadastro."""
    normalized = normalize_text(text)
    words = normalized.split()
    if not 2 <= len(words) <= 6 or any(char.isdigit() for char in normalized):
        return False
    blocked_terms = set("eu meu minha nome cpf nascimento consulta agendar marcar alergia coceira dor estou sinto quero".split())
    return not any(word in blocked_terms for word in words)


def _has_registration_context(messages: Sequence[Any]) -> bool:
    """Detecta continuidade do cadastro sem exigir nova chamada à LLM."""
    for message in reversed(messages or []):
        content = normalize_text(getattr(message, "content", ""))
        if getattr(message, "type", None) == "ai":
            if any(
                marker in content
                for marker in ("nome completo", "numero do cpf", "data de nascimento", "motivo da consulta")
            ):
                return True
        if getattr(message, "type", None) == "human" and any(
            term in content for term in ("agendar", "marcar consulta", "marcar uma consulta", "preciso marcar", "quero consulta")
        ):
            return True
    return False


class _Message:
    """Mensagem mínima para reutilizar extratores sem acoplar o router ao LangChain."""

    type = "human"

    def __init__(self, content: str):
        self.content = content
