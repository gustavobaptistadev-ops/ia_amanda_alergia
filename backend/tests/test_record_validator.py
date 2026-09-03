from langchain_core.messages import AIMessage, HumanMessage

from app.core.record_validator import validate_patient_record


def _complete_history(payment="Plano Bradesco"):
    return [
        HumanMessage(content="Quero marcar consulta porque estou com alergia nos braços"),
        AIMessage(content="Informe seu nome completo."),
        HumanMessage(content="Gustavo Henrique Baptista"),
        AIMessage(content="Informe seu CPF."),
        HumanMessage(content="00511483155"),
        AIMessage(content="Informe sua data de nascimento."),
        HumanMessage(content="04/08/1986"),
        AIMessage(content="Particular ou convênio?"),
        HumanMessage(content=payment),
    ]


def test_prontuario_completo_com_cpf_iniciado_em_zero_e_valido():
    result = validate_patient_record(_complete_history())

    assert result["valid"] is True
    assert result["missing_fields"] == []
    assert result["next_action"] == "CHECK_AVAILABILITY"


def test_cpf_invalido_bloqueia_agendamento_e_pede_somente_correcao():
    history = _complete_history()
    history[4] = HumanMessage(content="00511483156")

    result = validate_patient_record(history)

    assert result["valid"] is False
    assert result["invalid_fields"] == ["cpf"]
    assert result["next_action"] == "COLLECT_CPF"


def test_data_futura_bloqueia_agendamento():
    history = _complete_history()
    history[6] = HumanMessage(content="04/08/2090")

    result = validate_patient_record(history)

    assert result["valid"] is False
    assert result["invalid_fields"] == ["birth_date"]
    assert result["next_action"] == "COLLECT_BIRTH_DATE"


def test_dados_completos_na_mesma_mensagem_sao_validados():
    history = [HumanMessage(content=(
        "Quero consulta porque estou com alergia. Meu nome é Gustavo Henrique Baptista, "
        "CPF 00511483155, nascimento 04/08/1986, plano Bradesco."
    ))]

    result = validate_patient_record(history, {"entities": {"third_party": False}})

    assert result["valid"] is True
    assert set(result["fields_confirmed"]) == {"name", "cpf", "birth_date", "payment_type"}


def test_conflito_de_cpf_exige_revisao_humana():
    history = _complete_history()
    history.insert(5, HumanMessage(content="11144477735"))

    result = validate_patient_record(history)

    assert result["valid"] is False
    assert result["human_review_required"] is True
    assert "multiple_cpf_values" in result["conflicts"]
    assert result["next_action"] == "REVIEW_PATIENT_DATA"


def test_atendimento_para_terceiro_preserva_tipo_do_paciente():
    history = [
        HumanMessage(content="Quero agendar para minha filha, que está com alergia"),
        HumanMessage(content="Ana Clara Baptista"),
        HumanMessage(content="00511483155"),
        HumanMessage(content="04/08/2015"),
        HumanMessage(content="Particular"),
    ]

    result = validate_patient_record(history, {"entities": {"third_party": True}})

    assert result["patient_type"] == "third_party"
    assert result["valid"] is True
