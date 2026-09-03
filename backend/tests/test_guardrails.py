from app.core.guardrails import validar_resposta


def test_resposta_administrativa_nao_e_bloqueada_por_falso_positivo():
    resposta = (
        "Claro, Gustavo. Posso verificar os médicos disponíveis e as regras dos convênios "
        "para você escolher o melhor horário."
    )

    assert validar_resposta(resposta) is True


def test_resposta_com_orientacao_de_dose_continua_bloqueada():
    resposta = "Tome 10 mg de prednisona a cada oito horas."

    assert validar_resposta(resposta) is False
