import pytest

from app.services import evolution_api


def test_headers_falham_de_forma_segura_sem_token(monkeypatch):
    monkeypatch.delenv("EVOLUTION_API_KEY", raising=False)
    monkeypatch.setattr(evolution_api, "EVOLUTION_API_KEY", "")

    with pytest.raises(RuntimeError, match="EVOLUTION_API_KEY"):
        evolution_api.get_headers()


def test_headers_usam_somente_token_do_ambiente(monkeypatch):
    monkeypatch.setenv("EVOLUTION_API_KEY", "token-configurado-no-ambiente")

    headers = evolution_api.get_headers()

    assert headers["apikey"] == "token-configurado-no-ambiente"
    assert headers["Authorization"] == "Bearer token-configurado-no-ambiente"
