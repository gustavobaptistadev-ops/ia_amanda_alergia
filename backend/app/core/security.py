import os
import secrets

from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from app.core.config import settings

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
COOKIE_AUTH_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def require_secret(name: str, minimum_length: int = 32) -> str:
    value = getattr(settings, name, "").strip()
    if len(value) < minimum_length:
        raise RuntimeError(
            f"{name} must be configured with at least {minimum_length} characters"
        )
    return value


INTERNAL_API_KEY = require_secret("INTERNAL_API_KEY")
WEBHOOK_SECRET = require_secret("WEBHOOK_SECRET")


def _get_bearer_token(conn) -> str | None:
    auth_header = conn.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


async def _validate_jwt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        from app.core.auth import (
            ALGORITHM,
            SECRET_KEY,
            SESSION_TOKEN_VERSION,
            is_access_token_revoked,
        )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if (
            not payload.get("sub")
            or payload.get("ver") != SESSION_TOKEN_VERSION
            or await is_access_token_revoked(token)
        ):
            return None
        return token
    except JWTError:
        return None


def _allowed_browser_origins() -> set[str]:
    frontend_url = settings.FRONTEND_URL
    configured = settings.CORS_ORIGINS or frontend_url
    return {
        origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()
    }


def validate_cookie_origin(conn) -> None:
    """Prevent CSRF and cross-site WebSocket hijacking for cookie sessions."""
    origin = (conn.headers.get("origin") or "").rstrip("/")
    is_websocket = conn.scope.get("type") == "websocket"
    is_mutation = getattr(conn, "method", "GET").upper() in COOKIE_AUTH_METHODS
    if (is_websocket or is_mutation) and origin not in _allowed_browser_origins():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Origem não permitida"
        )


async def get_api_key(request: Request = None, websocket: WebSocket = None):
    conn = request or websocket
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação obrigatória"
        )

    key = conn.headers.get(API_KEY_NAME) or conn.headers.get(API_KEY_NAME.lower())
    if key and secrets.compare_digest(key, INTERNAL_API_KEY):
        return key

    token = _get_bearer_token(conn)
    cookie_token = None
    if not token and conn.scope.get("type") == "websocket":
        cookie_token = websocket.cookies.get("lifeline_session")
    elif not token:
        cookie_token = request.cookies.get("lifeline_session")
    if cookie_token:
        validate_cookie_origin(conn)
        token = cookie_token

    validated_token = await _validate_jwt(token)
    if validated_token:
        return validated_token

    if conn.scope.get("type") == "websocket":
        await conn.close(code=1008, reason="Authentication required")
        raise RuntimeError("WebSocket authentication failed")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou sessão expirada.",
    )
