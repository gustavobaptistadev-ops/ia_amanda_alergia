from langchain_core.messages import HumanMessage

from app.core.conversation_router import route_message


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
