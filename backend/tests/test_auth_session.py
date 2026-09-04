from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi import Response
from jose import jwt

from app.core import auth


def test_token_de_sessao_tem_identificador_e_expiracao_curta():
    token = auth.create_access_token(
        {"sub": "user-id"},
        expires_delta=timedelta(minutes=15),
    )

    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])

    assert payload["sub"] == "user-id"
    assert payload["jti"]
    assert payload["ver"] == auth.SESSION_TOKEN_VERSION
    assert payload["exp"] - payload["iat"] == 15 * 60


def test_cookie_http_only_substitui_token_do_javascript():
    request = SimpleNamespace(cookies={auth.SESSION_COOKIE_NAME: "cookie-token"})

    assert auth.get_request_token(request) == "cookie-token"
    assert auth.get_request_token(request, "bearer-token") == "bearer-token"


def test_chave_de_revogacao_nao_armazena_o_token_bruto():
    token = "header.payload.signature"

    key = auth._revocation_key(token)

    assert token not in key
    assert key.startswith(auth.REVOCATION_KEY_PREFIX)


def test_cookie_de_sessao_nao_fica_acessivel_ao_javascript():
    response = Response()

    auth.set_session_cookie(response, "signed-token")
    cookie = response.headers["set-cookie"].lower()

    assert "lifeline_session=" in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=none" in cookie
    assert "max-age=3600" in cookie


@pytest.mark.asyncio
async def test_logout_revoga_token_ate_a_expiracao(monkeypatch):
    writes = []

    class FakeRedis:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def setex(self, key, ttl, value):
            writes.append((key, ttl, value))

    import redis.asyncio as redis

    monkeypatch.setattr(redis.Redis, "from_url", lambda *_args, **_kwargs: FakeRedis())
    token = auth.create_access_token(
        {"sub": "user-id"},
        expires_delta=timedelta(minutes=15),
    )

    await auth.revoke_access_token(token)

    assert len(writes) == 1
    assert 1 <= writes[0][1] <= 15 * 60
    assert writes[0][2] == "1"
