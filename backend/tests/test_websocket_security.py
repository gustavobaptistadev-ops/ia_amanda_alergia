from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.security import validate_cookie_origin
from app.core.config import settings

def _connection(origin: str, connection_type: str = "websocket", method: str = "GET"):
    return SimpleNamespace(
        headers={"origin": origin},
        scope={"type": connection_type},
        method=method,
    )


def test_websocket_aceita_origem_do_frontend(monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://painel.example.com")

    validate_cookie_origin(_connection("https://painel.example.com"))


def test_websocket_rejeita_origem_externa(monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://painel.example.com")

    with pytest.raises(HTTPException) as error:
        validate_cookie_origin(_connection("https://site-malicioso.example"))

    assert error.value.status_code == 403


def test_requisicao_mutavel_por_cookie_exige_origem_permitida(monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://painel.example.com")

    with pytest.raises(HTTPException) as error:
        validate_cookie_origin(
            _connection("https://site-malicioso.example", "http", "POST")
        )

    assert error.value.status_code == 403


def test_leitura_http_nao_exige_origin():
    validate_cookie_origin(_connection("", "http", "GET"))
