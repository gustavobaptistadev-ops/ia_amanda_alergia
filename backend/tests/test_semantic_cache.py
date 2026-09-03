from app.services.semantic_cache import (
    generate_cache_key,
    is_dynamic_conversation_message,
    is_public_cache_response,
    is_public_faq_message,
)


def test_data_de_nascimento_nao_pode_ser_cacheada():
    assert is_dynamic_conversation_message("04/08/1986") is True


def test_escolha_de_dia_e_horario_nao_pode_ser_cacheada():
    assert is_dynamic_conversation_message("Sexta às 15") is True


def test_duvida_estatica_pode_ser_considerada_para_cache():
    assert is_dynamic_conversation_message("Quais procedimentos a clínica realiza?") is False


def test_cache_aceita_apenas_pergunta_publica_da_clinica():
    assert is_public_faq_message("Quais procedimentos a clínica realiza?") is True
    assert is_public_faq_message("Quais convênios vocês aceitam?") is True
    assert is_public_faq_message("Plano Bradesco") is False
    assert is_public_faq_message("Sexta às 17") is False
    assert is_public_faq_message("Gustavo Henrique Baptista") is False


def test_cache_rejeita_resposta_transacional_ou_link_pessoal():
    assert is_public_cache_response("Realizamos testes alérgicos e consultas.") is True
    assert is_public_cache_response("Agora informe seu CPF, por favor.") is False
    assert is_public_cache_response("Adicione em /calendar/p/identificador") is False


def test_cache_novo_nao_reutiliza_entradas_legadas():
    assert generate_cache_key("Quais procedimentos?").startswith("semantic_cache:v2:")
