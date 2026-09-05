"""Estado persistente e transições determinísticas do fluxo de agendamento."""

import datetime as dt
import re
from collections.abc import Sequence
from typing import Any

from app.core.conversation_router import extract_requested_date, normalize_text
from app.core.patient_data import (
    contains_date,
    extract_clinical_summary,
    extract_cpf_from_text,
    extract_email,
    extract_latest_cpf,
    extract_latest_date,
    extract_medications,
    extract_payment_type,
    has_patient_complaint,
    has_symptom_duration,
)

ACTIVE_STAGES = {
    "AWAITING_COMPLAINT",
    "AWAITING_PATIENT_NAME",
    "AWAITING_CPF",
    "AWAITING_BIRTH_DATE",
    "AWAITING_EMAIL",
    "AWAITING_PAYMENT",
    "AWAITING_INSURANCE_CARD",
    "READY_FOR_AVAILABILITY",
    "AWAITING_SLOT",
    "READY_TO_BOOK",
    "HUMAN_REVIEW",
}

ACTION_BY_STAGE = {
    "AWAITING_COMPLAINT": "COLLECT_COMPLAINT",
    "AWAITING_PATIENT_NAME": "COLLECT_NAME",
    "AWAITING_CPF": "COLLECT_CPF",
    "AWAITING_BIRTH_DATE": "COLLECT_BIRTH_DATE",
    "AWAITING_EMAIL": "COLLECT_EMAIL",
    "AWAITING_PAYMENT": "COLLECT_PAYMENT_TYPE",
    "AWAITING_INSURANCE_CARD": "COLLECT_INSURANCE_CARD",
    "READY_FOR_AVAILABILITY": "CHECK_AVAILABILITY",
    "AWAITING_SLOT": "AWAIT_SLOT",
    "READY_TO_BOOK": "CONFIRM_SLOT",
    "HUMAN_REVIEW": "REVIEW_PATIENT_DATA",
    "BOOKED": "BOOKED",
}


def new_booking_state() -> dict[str, Any]:
    return {
        "version": 2,
        "stage": "NEW",
        "patient_type": "self",
        "complaint_collected": False,
        "duration_collected": False,
        "medication_collected": False,
        "clinical_summary": None,
        "patient_name": None,
        "cpf": None,
        "birth_date": None,
        "email": None,
        "payment_type": None,
        "insurance_operator": None,
        "insurance_card": None,
        "offered_slots": [],
        "selected_slot": None,
        "requested_date": None,
        "conflicts": [],
        "booking_status": "collecting",
        "appointment_id": None,
    }


def _clean_text(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("<user_message>") and cleaned.endswith("</user_message>"):
        cleaned = cleaned[len("<user_message>") : -len("</user_message>")]
    return cleaned.strip()


def _is_correction(text: str) -> bool:
    normalized = normalize_text(text)
    return any(
        term in normalized
        for term in ("corrig", "correcao", "correto", "correta", "errei", "na verdade")
    )


def _normalize_birth_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = (
            dt.datetime.strptime(value, "%d/%m/%Y").date()
            if "/" in value
            else dt.date.fromisoformat(value)
        )
    except ValueError:
        return None
    today = dt.date.today()
    if parsed > today or parsed < today.replace(year=today.year - 120):
        return None
    return parsed.isoformat()


def _extract_name(text: str, routing: dict[str, Any], expected: bool) -> str | None:
    routed_name = routing.get("entities", {}).get("name")
    if routed_name:
        return re.sub(r"\s+", " ", routed_name).strip(" .,!?\n\r\t")
    if not expected:
        return None
    candidate = _clean_text(text).strip(" .,!?\n\r\t")
    words = candidate.split()
    if 2 <= len(words) <= 8 and not any(char.isdigit() for char in candidate):
        blocked = (
            "consulta",
            "alergia",
            "cpf",
            "nascimento",
            "plano",
            "particular",
            "convenio",
        )
        if not any(term in normalize_text(candidate) for term in blocked):
            return re.sub(r"\s+", " ", candidate)
    return None


def _insurance_operator(text: str, payment_type: str | None) -> str | None:
    if payment_type != "convenio":
        return None
    normalized = normalize_text(text)
    operators = {
        "bradesco": "Bradesco",
        "unimed": "Unimed",
        "amil": "Amil",
        "sulamerica": "SulAmérica",
        "sul america": "SulAmérica",
        "assefaz": "Assefaz",
        "geap": "Geap",
        "cassi": "Cassi",
        "hapvida": "Hapvida",
    }
    return next((label for term, label in operators.items() if term in normalized), None)


def _select_offered_slot(
    text: str, slots: Sequence[dict[str, str]]
) -> dict[str, str] | None:
    normalized = normalize_text(text)
    time_match = re.search(
        r"\b(?:as|a|pelas?)\s*(\d{1,2})(?::(\d{2}))?\s*h?\b", normalized
    )
    if not time_match:
        return None
    selected_time = f"{int(time_match.group(1)):02d}:{time_match.group(2) or '00'}"
    candidates = [slot for slot in slots if slot.get("time") == selected_time]
    if not candidates:
        return None

    weekday_indexes = {
        "segunda": 0,
        "terca": 1,
        "quarta": 2,
        "quinta": 3,
        "sexta": 4,
        "sabado": 5,
        "domingo": 6,
    }
    requested_weekday = next(
        (index for label, index in weekday_indexes.items() if label in normalized),
        None,
    )
    if requested_weekday is not None:
        weekday_matches = []
        for slot in candidates:
            try:
                if (
                    dt.date.fromisoformat(slot.get("date", "")).weekday()
                    == requested_weekday
                ):
                    weekday_matches.append(slot)
            except ValueError:
                continue
        return dict(weekday_matches[0]) if len(weekday_matches) == 1 else None

    explicit_date = extract_requested_date(text)
    if explicit_date:
        exact = [slot for slot in candidates if slot.get("date") == explicit_date]
        return dict(exact[0]) if len(exact) == 1 else None
    return dict(candidates[0]) if len(candidates) == 1 else None


def _derive_stage(booking: dict[str, Any]) -> str:
    if booking.get("booking_status") == "booked":
        return "BOOKED"
    if booking.get("conflicts"):
        return "HUMAN_REVIEW"
    if (
        not booking.get("complaint_collected")
        or not booking.get("duration_collected")
        or not booking.get("medication_collected")
    ):
        return "AWAITING_COMPLAINT"
    if not booking.get("patient_name"):
        return "AWAITING_PATIENT_NAME"
    if not booking.get("cpf"):
        return "AWAITING_CPF"
    if not booking.get("birth_date"):
        return "AWAITING_BIRTH_DATE"
    if not booking.get("email"):
        return "AWAITING_EMAIL"
    if not booking.get("payment_type"):
        return "AWAITING_PAYMENT"
    if booking.get("payment_type") == "convenio" and not booking.get("insurance_card"):
        return "AWAITING_INSURANCE_CARD"
    if booking.get("selected_slot"):
        return "READY_TO_BOOK"
    if booking.get("requested_date") or not booking.get("offered_slots"):
        return "READY_FOR_AVAILABILITY"
    return "AWAITING_SLOT"


def update_booking_state(
    previous: dict[str, Any] | None,
    text: str,
    messages: Sequence[Any],
    routing: dict[str, Any],
) -> dict[str, Any]:
    """Acumula dados confirmados sem apagá-los quando o histórico for podado."""
    booking = {**new_booking_state(), **(previous or {})}
    clean_text = _clean_text(text)
    was_active = booking.get("stage") in ACTIVE_STAGES
    is_scheduling = routing.get("intent") == "AGENDAMENTO" or was_active
    if not is_scheduling or booking.get("stage") == "BOOKED":
        return booking

    entities = routing.get("entities", {})
    booking["patient_type"] = (
        "third_party"
        if entities.get("third_party")
        else booking.get("patient_type", "self")
    )
    booking["complaint_collected"] = bool(
        booking.get("complaint_collected")
        or entities.get("complaint_detected")
        or has_patient_complaint(messages)
    )
    booking["duration_collected"] = bool(
        booking.get("duration_collected")
        or entities.get("duration_detected")
        or has_symptom_duration(messages)
    )
    booking["medication_collected"] = bool(
        booking.get("medication_collected")
        or entities.get("medication_detected")
        or len(extract_medications(messages)) > 0
    )

    # On NEW, accept only names explicitly extracted by the router (for example,
    # "meu nome e ..."). Free text becomes a name only after we asked for it.
    expected_name = booking.get("stage") == "AWAITING_PATIENT_NAME"
    new_name = _extract_name(clean_text, routing, expected_name)
    if new_name and (not booking.get("patient_name") or _is_correction(clean_text)):
        booking["patient_name"] = new_name

    new_cpf = extract_cpf_from_text(clean_text)
    if not new_cpf and not booking.get("cpf"):
        new_cpf = extract_latest_cpf(messages)
    if new_cpf:
        if (
            booking.get("cpf")
            and booking["cpf"] != new_cpf
            and not _is_correction(clean_text)
        ):
            booking["conflicts"] = sorted(
                set(booking.get("conflicts", []) + ["cpf_conflict"])
            )
        else:
            booking["cpf"] = new_cpf
            if _is_correction(clean_text):
                booking["conflicts"] = [
                    item
                    for item in booking.get("conflicts", [])
                    if item != "cpf_conflict"
                ]

    new_birth_date = None
    if contains_date(clean_text) and (
        booking.get("stage") in {"NEW", "AWAITING_BIRTH_DATE"}
        or "nascimento" in normalize_text(clean_text)
    ):
        date_match = re.search(r"\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}", clean_text)
        new_birth_date = _normalize_birth_date(
            date_match.group(0) if date_match else None
        )
    if not new_birth_date and not booking.get("birth_date"):
        new_birth_date = _normalize_birth_date(extract_latest_date(messages))
    if new_birth_date:
        if (
            booking.get("birth_date")
            and booking["birth_date"] != new_birth_date
            and not _is_correction(clean_text)
        ):
            booking["conflicts"] = sorted(
                set(booking.get("conflicts", []) + ["birth_date_conflict"])
            )
        else:
            booking["birth_date"] = new_birth_date
            if _is_correction(clean_text):
                booking["conflicts"] = [
                    item
                    for item in booking.get("conflicts", [])
                    if item != "birth_date_conflict"
                ]

    if (
        booking.get("complaint_collected")
        and booking.get("duration_collected")
        and booking.get("medication_collected")
        and not booking.get("clinical_summary")
    ):
        booking["clinical_summary"] = extract_clinical_summary(messages)

    new_email = extract_email(clean_text)
    if new_email:
        if (
            booking.get("email")
            and booking["email"] != new_email
            and not _is_correction(clean_text)
        ):
            booking["conflicts"] = sorted(
                set(booking.get("conflicts", []) + ["email_conflict"])
            )
        else:
            booking["email"] = new_email
            if _is_correction(clean_text):
                booking["conflicts"] = [
                    item
                    for item in booking.get("conflicts", [])
                    if item != "email_conflict"
                ]

    payment_type = extract_payment_type([_HumanMessage(clean_text)])
    if payment_type:
        booking["payment_type"] = payment_type
        booking["insurance_operator"] = _insurance_operator(clean_text, payment_type)

    if booking.get("stage") == "AWAITING_INSURANCE_CARD":
        if len(clean_text) >= 5:  # basic validation for card number
            booking["insurance_card"] = clean_text

    selected_slot = _select_offered_slot(clean_text, booking.get("offered_slots", []))
    if selected_slot:
        booking["selected_slot"] = selected_slot
        booking["requested_date"] = None
    elif booking.get("offered_slots"):
        requested_date = extract_requested_date(clean_text)
        offered_dates = {slot.get("date") for slot in booking["offered_slots"]}
        if requested_date and requested_date not in offered_dates:
            booking["requested_date"] = requested_date
            booking["selected_slot"] = None

    booking["stage"] = _derive_stage(booking)
    return booking


def set_offered_slots(
    booking: dict[str, Any], slots: Sequence[dict[str, str]]
) -> dict[str, Any]:
    updated = {**booking}
    updated["offered_slots"] = [dict(slot) for slot in slots]
    updated["selected_slot"] = None
    updated["requested_date"] = None
    updated["stage"] = "AWAITING_SLOT" if slots else "READY_FOR_AVAILABILITY"
    return updated


def mark_booking_created(
    booking: dict[str, Any], appointment_id: str | None = None
) -> dict[str, Any]:
    updated = {**booking}
    updated["booking_status"] = "booked"
    updated["appointment_id"] = appointment_id
    updated["stage"] = "BOOKED"
    return updated


def booking_next_action(booking: dict[str, Any]) -> str:
    return ACTION_BY_STAGE.get(booking.get("stage", "NEW"), "COLLECT_COMPLAINT")


def booking_is_active(booking: dict[str, Any] | None) -> bool:
    return bool(booking and booking.get("stage") in ACTIVE_STAGES)


def validate_booking_state(booking: dict[str, Any]) -> dict[str, Any]:
    required = ["patient_name", "cpf", "birth_date", "email", "payment_type"]
    missing = [field for field in required if not booking.get(field)]

    if booking.get("payment_type") == "convenio" and not booking.get("insurance_card"):
        missing.append("insurance_card")

    return {
        "valid": bool(
            booking.get("complaint_collected")
            and booking.get("duration_collected")
            and booking.get("medication_collected")
        )
        and not missing
        and not booking.get("conflicts"),
        "patient_type": booking.get("patient_type", "self"),
        "missing_fields": missing,
        "conflicts": list(booking.get("conflicts", [])),
        "next_action": booking_next_action(booking),
        "human_review_required": bool(booking.get("conflicts")),
    }


class _HumanMessage:
    type = "human"

    def __init__(self, content: str):
        self.content = content
