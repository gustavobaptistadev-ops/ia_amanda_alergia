from app.services.semantic_cache import is_dynamic_conversation_message


def test_data_de_nascimento_nao_pode_ser_cacheada():
    assert is_dynamic_conversation_message("04/08/1986") is True


def test_escolha_de_dia_e_horario_nao_pode_ser_cacheada():
    assert is_dynamic_conversation_message("Sexta às 15") is True


def test_duvida_estatica_pode_ser_considerada_para_cache():
    assert is_dynamic_conversation_message("Quais procedimentos a clínica realiza?") is False
