from langchain_core.messages import AIMessage, HumanMessage

from app.core.conversation_router import route_message
from app.core.response_quality import assess_response_quality


def test_agendamento_sem_queixa_pede_motivo_antes_do_cadastro():
    decision = route_message("Preciso marcar uma consulta", [])

    assert decision["intent"] == "AGENDAMENTO"
    assert decision["confidence"] >= 0.90
    assert decision["next_action"] == "COLLECT_COMPLAINT"


def test_agendamento_com_queixa_identifica_proximo_dado():
    decision = route_message(
        "Quero agendar porque estou com alergia e coceira",
        [HumanMessage(content="Quero agendar porque estou com alergia e coceira")],
    )

    assert decision["entities"]["third_party"] is False
    assert decision["next_action"] == "COLLECT_NAME"


def test_agendamento_para_terceiro_preserva_a_distincao_do_responsavel():
    decision = route_message("Quero marcar uma consulta para minha filha", [])

    assert decision["entities"]["third_party"] is True
    assert decision["next_action"] == "COLLECT_COMPLAINT"


def test_resposta_curta_mantem_o_fluxo_de_cadastro():
    decision = route_message(
        "Gustavo Henrique Baptista",
        [
            HumanMessage(content="Preciso marcar uma consulta"),
            HumanMessage(content="Estou com alergia"),
        ],
    )

    assert decision["intent"] == "AGENDAMENTO"
    assert decision["next_action"] == "COLLECT_CPF"


def test_nome_curto_persistido_no_historico_permite_avancar_apos_cpf():
    history = [
        HumanMessage(content="Preciso marcar uma consulta"),
        AIMessage(content="Qual o motivo da consulta?"),
        HumanMessage(content="Meus braços estão com alergia"),
        AIMessage(content="Informe seu nome completo, por favor."),
        HumanMessage(content="Gustavo Henrique Baptista"),
        AIMessage(content="Agora informe o seu CPF, por favor."),
    ]

    decision = route_message("00511483155", history)

    assert decision["entities"]["cpf"] == "00511483155"
    assert decision["next_action"] == "COLLECT_BIRTH_DATE"


def test_quality_gate_reprova_resposta_que_volta_a_pedir_nome_apos_cpf():
    adequate, reason = assess_response_quality(
        "Para abrir o cadastro, informe seu nome completo, por favor.",
        {"next_action": "COLLECT_BIRTH_DATE"},
    )

    assert adequate is False
    assert reason == "etapa_nascimento_voltou_ao_nome"


def test_quality_gate_aprova_resposta_coerente_com_cpf():
    adequate, reason = assess_response_quality(
        "Obrigado. Agora informe sua data de nascimento, por favor.",
        {"next_action": "COLLECT_BIRTH_DATE"},
    )

    assert adequate is True
    assert reason == "ok"


def test_escolha_de_horario_avanca_para_confirmacao_do_agendamento():
    history = [
        HumanMessage(content="Quero marcar uma consulta"),
        AIMessage(content="Qual o motivo da consulta?"),
        HumanMessage(content="Estou com alergia nos braços"),
        AIMessage(content="Informe seu nome completo, por favor."),
        HumanMessage(content="Gustavo Henrique Baptista"),
        AIMessage(content="Agora informe seu CPF."),
        HumanMessage(content="00511483155"),
        AIMessage(content="Informe sua data de nascimento."),
        HumanMessage(content="04/08/1986"),
        AIMessage(content="Temos horários disponíveis: Sexta-feira, 04/09: 11:00, 15:00, 16:00."),
    ]

    decision = route_message("Sexta às 15", history)

    assert decision["next_action"] == "CONFIRM_SLOT"
    assert decision["entities"]["name"] == "Gustavo Henrique Baptista"
    assert decision["entities"]["cpf"] is None
    assert decision["entities"]["preferred_slot"] == {"date": "2026-09-04", "time": "15:00"}
