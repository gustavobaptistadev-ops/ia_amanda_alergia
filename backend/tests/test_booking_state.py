from langchain_core.messages import HumanMessage

from app.core.booking_state import (
    booking_is_active,
    booking_next_action,
    mark_booking_created,
    new_booking_state,
    set_offered_slots,
    update_booking_state,
    validate_booking_state,
)


def _routing(*, complaint=False, third_party=False, name=None):
    return {
        "intent": "AGENDAMENTO",
        "entities": {
            "complaint_detected": complaint,
            "third_party": third_party,
            "name": name,
        },
    }


def _advance(state, text, routing=None):
    return update_booking_state(
        state,
        text,
        [HumanMessage(content=text)],
        routing or _routing(),
    )


def _complete_registration():
    state = _advance(None, "Quero marcar consulta")
    assert booking_next_action(state) == "COLLECT_COMPLAINT"

    state = _advance(state, "Estou com alergia nos bracos", _routing(complaint=True))
    assert booking_next_action(state) == "COLLECT_NAME"

    state = _advance(state, "Gustavo Henrique Baptista")
    assert booking_next_action(state) == "COLLECT_CPF"

    state = _advance(state, "00511483155")
    assert state["cpf"] == "00511483155"
    assert booking_next_action(state) == "COLLECT_BIRTH_DATE"

    state = _advance(state, "04/08/1986")
    assert booking_next_action(state) == "COLLECT_PAYMENT_TYPE"

    state = _advance(state, "Plano Bradesco")
    assert booking_next_action(state) == "CHECK_AVAILABILITY"
    return state


def test_fluxo_completo_nao_regride_quando_historico_foi_podado():
    state = _complete_registration()

    assert validate_booking_state(state)["valid"] is True
    assert state["patient_name"] == "Gustavo Henrique Baptista"
    assert state["birth_date"] == "1986-08-04"
    assert state["payment_type"] == "convenio"
    assert state["insurance_operator"] == "Bradesco"

    state = set_offered_slots(state, [
        {"date": "2026-09-04", "time": "17:00"},
        {"date": "2026-09-05", "time": "08:30"},
    ])
    state = _advance(state, "Sexta as 17")

    assert booking_next_action(state) == "CONFIRM_SLOT"
    assert state["selected_slot"] == {"date": "2026-09-04", "time": "17:00"}
    assert state["patient_name"] == "Gustavo Henrique Baptista"
    assert state["cpf"] == "00511483155"
    assert state["birth_date"] == "1986-08-04"


def test_horario_so_e_aceito_quando_foi_oferecido():
    state = set_offered_slots(_complete_registration(), [
        {"date": "2026-09-04", "time": "17:00"},
        {"date": "2026-09-05", "time": "08:30"},
    ])

    state = _advance(state, "Sexta as 16")

    assert booking_next_action(state) == "AWAIT_SLOT"
    assert state["selected_slot"] is None


def test_mesmo_horario_em_dois_dias_exige_identificacao_do_dia():
    state = set_offered_slots(_complete_registration(), [
        {"date": "2026-09-04", "time": "17:00"},
        {"date": "2026-09-05", "time": "17:00"},
    ])

    ambiguous = _advance(state, "As 17")
    selected = _advance(state, "Sabado as 17")

    assert booking_next_action(ambiguous) == "AWAIT_SLOT"
    assert selected["selected_slot"] == {"date": "2026-09-05", "time": "17:00"}


def test_pedido_de_outro_dia_dispara_nova_consulta_de_disponibilidade():
    state = set_offered_slots(_complete_registration(), [
        {"date": "2026-09-04", "time": "17:00"},
        {"date": "2026-09-05", "time": "08:30"},
    ])

    state = _advance(state, "Prefiro dia 08/09/2026")

    assert booking_next_action(state) == "CHECK_AVAILABILITY"
    assert state["requested_date"] == "2026-09-08"


def test_agendamento_para_terceiro_preserva_o_tipo_do_paciente():
    state = _advance(
        None,
        "Quero marcar para minha filha",
        _routing(third_party=True),
    )
    state = _advance(
        state,
        "Ela esta com alergia",
        _routing(complaint=True, third_party=True),
    )

    assert state["patient_type"] == "third_party"
    assert booking_next_action(state) == "COLLECT_NAME"


def test_dado_confirmado_so_muda_com_correcao_explicita():
    state = _complete_registration()

    conflict = _advance(state, "Meu CPF e 52998224725")
    corrected = _advance(conflict, "Correcao: meu CPF e 52998224725")

    assert booking_next_action(conflict) == "REVIEW_PATIENT_DATA"
    assert conflict["cpf"] == "00511483155"
    assert corrected["cpf"] == "52998224725"
    assert corrected["conflicts"] == []


def test_estado_confirmado_nao_reabre_o_cadastro():
    state = set_offered_slots(_complete_registration(), [
        {"date": "2026-09-04", "time": "17:00"},
    ])
    state = _advance(state, "As 17")
    state = mark_booking_created(state, "appointment-id")

    repeated = _advance(state, "Estou com alergia")

    assert booking_next_action(repeated) == "BOOKED"
    assert repeated["appointment_id"] == "appointment-id"
    assert booking_is_active(repeated) is False


def test_novo_estado_possui_contrato_versionado():
    state = new_booking_state()

    assert state["version"] == 2
    assert state["stage"] == "NEW"
    assert state["offered_slots"] == []
