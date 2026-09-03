import os
import secrets

from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def require_secret(name: str, minimum_length: int = 32) -> str:
    value = os.getenv(name, "").strip()
    if len(value) < minimum_length:
        raise RuntimeError(f"{name} must be configured with at least {minimum_length} characters")
    return value


INTERNAL_API_KEY = require_secret("INTERNAL_API_KEY")
WEBHOOK_SECRET = require_secret("WEBHOOK_SECRET")


def _get_bearer_token(conn) -> str | None:
    auth_header = conn.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


def _validate_jwt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        from app.core.auth import ALGORITHM, SECRET_KEY

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return token if payload.get("sub") else None
    except JWTError:
        return None


async def get_api_key(request: Request = None, websocket: WebSocket = None):
    conn = request or websocket
    if not conn:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação obrigatória")

    key = conn.headers.get(API_KEY_NAME) or conn.headers.get(API_KEY_NAME.lower())
    if key and secrets.compare_digest(key, INTERNAL_API_KEY):
        return key

    token = _get_bearer_token(conn)
    if not token and conn.scope.get("type") == "websocket":
        token = conn.query_params.get("access_token")

    validated_token = _validate_jwt(token)
    if validated_token:
        return validated_token

    if conn.scope.get("type") == "websocket":
        await conn.close(code=1008, reason="Authentication required")
        raise RuntimeError("WebSocket authentication failed")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas ou sessão expirada.")
