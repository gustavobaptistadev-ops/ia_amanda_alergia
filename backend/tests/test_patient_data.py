from langchain_core.messages import AIMessage, HumanMessage

from app.core.patient_data import contains_date, extract_cpf_from_text, extract_latest_cpf, has_patient_complaint
from app.services.evolution_api import repair_mojibake


def test_cpf_with_leading_zeros_is_preserved():
    assert extract_cpf_from_text("00511483155") == "00511483155"


def test_formatted_cpf_is_normalized():
    assert extract_cpf_from_text("005.114.831-55") == "00511483155"


def test_latest_cpf_ignores_ai_messages():
    messages = [
        HumanMessage(content="Meu nome é Gustavo Henrique"),
        AIMessage(content="Qual é o seu CPF?"),
        HumanMessage(content="00511483155"),
    ]
    assert extract_latest_cpf(messages) == "00511483155"


def test_birth_date_is_detected_without_affecting_cpf_format():
    assert contains_date("Nascimento 04/08/1986")


def test_complaint_is_required_before_registration():
    messages = [HumanMessage(content="Preciso marcar uma consulta")]

    assert has_patient_complaint(messages) is False


def test_complaint_can_be_detected_in_same_booking_message():
    messages = [HumanMessage(content="Quero agendar porque estou com alergia e coceira")]

    assert has_patient_complaint(messages) is True


def test_resposta_legada_com_encoding_quebrado_e_corrigida_na_saida():
    assert repair_mojibake("Sua consulta estÃƒÂ¡ confirmada. VocÃƒÂª jÃƒÂ¡ pode ir.") == (
        "Sua consulta está confirmada. Você já pode ir."
    )
