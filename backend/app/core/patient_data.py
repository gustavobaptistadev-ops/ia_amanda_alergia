import re
import unicodedata
from collections.abc import Sequence

from app.core.validators import validate_cpf

CPF_CANDIDATE_PATTERN = re.compile(r"(?<!\d)(?:\d[ .-]?){10}\d(?!\d)")
DATE_PATTERN = re.compile(r"(?<!\d)(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{8})(?!\d)")
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
            val = match.group(0)
            if len(val) == 8 and val.isdigit():
                return f"{val[:2]}/{val[2:4]}/{val[4:]}"
            return val
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

import json
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from app.api.endpoints.settings import load_config
from langchain_core.messages import BaseMessage

class PatientProfile(BaseModel):
    patient_name: Optional[str] = Field(description="Nome completo do paciente.")
    cpf: Optional[str] = Field(description="CPF do paciente contendo APENAS números.")
    birth_date: Optional[str] = Field(description="Data de nascimento do paciente SEMPRE e OBRIGATORIAMENTE convertida no formato YYYY-MM-DD. (ex: se for 04081986, retorne 1986-08-04)")
    email: Optional[str] = Field(description="Endereço de e-mail do paciente.")
    payment_type: Optional[Literal["convenio", "particular"]] = Field(description="Tipo de pagamento (convenio ou particular).")
    insurance_operator: Optional[str] = Field(description="Nome da operadora do convênio de saúde (ex: Bradesco, Unimed).")
    insurance_card: Optional[str] = Field(description="Número da carteirinha do convênio.")
    symptoms: Optional[str] = Field(description="Resumo claro e descritivo dos sintomas relatados pelo paciente (ex: 'alergia nas pernas após ir à praia').")
    symptoms_duration: Optional[str] = Field(description="Duração relatada dos sintomas (ex: '3 dias', 'desde ontem').")
    medications: list[str] = Field(default_factory=list, description="Remédios que o paciente informou estar tomando (ou pomadas, etc).")

def extract_patient_profile(messages: Sequence[BaseMessage], current_profile: dict) -> dict:
    """Usa a LLM para ler o histórico e atualizar o perfil do paciente iterativamente."""
    cfg = load_config()
    model_name = cfg.get("model", "gpt-4o-mini")
    # Temperature 0 is ideal for data extraction
    llm = ChatOpenAI(model=model_name, temperature=0.0).with_structured_output(PatientProfile)
    
    transcript = "\n".join(
        f"{'PACIENTE' if getattr(msg, 'type', '') == 'human' else 'AMANDA'}: {getattr(msg, 'content', '')}"
        for msg in messages[-10:] if getattr(msg, "content", "")
    )
    
    prompt = f"""Você é um extrator de memória para prontuário médico. Sua missão é mesclar os dados conhecidos do paciente com novas informações reveladas na conversa.
Seja inteligente: se o paciente jogar dados soltos como "4081986", perceba que é a data de nascimento e converta estritamente para formato YYYY-MM-DD (1986-08-04).
Se enviar um número parecido com CPF, remova pontuação e guarde no CPF.

PERFIL ATUAL CONHECIDO:
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

CONVERSA RECENTE:
{transcript}

Retorne OBRIGATORIAMENTE as informações consolidadas. Se o Perfil Atual já tem o CPF, mantenha o CPF. Apenas atualize ou adicione o que o paciente informou de novo. Se um dado não foi mencionado, ignore.
"""
    try:
        updated_profile = llm.invoke(prompt)
        # Convert to dict keeping only populated fields
        new_dict = updated_profile.model_dump(exclude_unset=True, exclude_none=True)
        # Merge dictionaries explicitly, updating current profile with new extracted data
        merged = {**current_profile}
        
        for k, v in new_dict.items():
            if isinstance(v, list):
                # Merge lists
                merged_list = set(merged.get(k) or [])
                merged_list.update(v)
                merged[k] = list(merged_list)
            elif v is not None and v != "":
                merged[k] = v
                
        return merged
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Erro na extração de PatientProfile: {e}")
        return current_profile

