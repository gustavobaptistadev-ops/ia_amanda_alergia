import os
import secrets

from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt

API_KEY_NAME = "X-API-Key"
WEBSOCKET_AUTH_PROTOCOL = "bearer"
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


def get_websocket_protocol_token(websocket: WebSocket) -> str | None:
    """Read a JWT from the WebSocket protocol header without exposing it in the URL."""
    raw_protocols = websocket.headers.get("sec-websocket-protocol", "")
    protocols = [item.strip() for item in raw_protocols.split(",") if item.strip()]
    if len(protocols) >= 2 and secrets.compare_digest(
        protocols[0].lower(), WEBSOCKET_AUTH_PROTOCOL
    ):
        return protocols[1]
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
        token = get_websocket_protocol_token(websocket)

    validated_token = _validate_jwt(token)
    if validated_token:
        return validated_token

    if conn.scope.get("type") == "websocket":
        await conn.close(code=1008, reason="Authentication required")
        raise RuntimeError("WebSocket authentication failed")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas ou sessão expirada.")
