"""Valida regras essenciais antes de uma resposta chegar ao paciente."""

import re
from typing import Any


INTERNAL_LEAK_PATTERNS = (
    r"\bsystem prompt\b",
    r"\binstru[cç][oõ]es internas\b",
    r"\b(api|webhook|jwt|database|postgres|redis|tool_calls?)\b",
    r"\berro\s*(500|401|403|404)\b",
)

EXPECTED_TERMS = {
    "COLLECT_COMPLAINT": ("motivo", "sentindo", "sente", "queixa", "avaliação", "avaliacao"),
    "COLLECT_NAME": ("nome completo", "nome da pessoa"),
    "COLLECT_CPF": ("cpf",),
    "COLLECT_BIRTH_DATE": ("nascimento", "data de nascimento"),
}


def assess_response_quality(response: str, routing: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Verifica se a resposta está coerente com o estado sem consumir LLM."""
    text = str(response or "").strip()
    if not text:
        return False, "resposta_vazia"
    if len(text) > 1600:
        return False, "resposta_muito_longa"

    normalized = re.sub(r"\s+", " ", text.lower())
    if any(re.search(pattern, normalized) for pattern in INTERNAL_LEAK_PATTERNS):
        return False, "possivel_vazamento_interno"

    next_action = (routing or {}).get("next_action")
    # Uma etapa deve solicitar apenas o dado atualmente faltante.
    if next_action == "COLLECT_NAME" and "cpf" in normalized:
        return False, "etapa_nome_misturada_com_cpf"
    if next_action == "COLLECT_CPF" and "data de nascimento" in normalized:
        return False, "etapa_cpf_misturada_com_nascimento"
    if next_action == "COLLECT_BIRTH_DATE" and "nome completo" in normalized:
        return False, "etapa_nascimento_voltou_ao_nome"

    expected_terms = EXPECTED_TERMS.get(next_action, ())
    if expected_terms and not any(term in normalized for term in expected_terms):
        return False, f"acao_{next_action}_nao_confirmada"

    return True, "ok"
