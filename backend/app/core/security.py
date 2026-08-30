from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
import os
import secrets

API_KEY_NAME = 'X-API-Key'
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', 'dev-secret-key-123')

async def get_api_key(request: Request, key: str = Security(api_key_header)):
    # 1. Permite upgrade transparente de conexões WebSocket
    if request.scope.get("type") == "websocket":
        return None

    # 2. Valida chave interna direta (X-API-Key)
    if key and secrets.compare_digest(key, INTERNAL_API_KEY):
        return key

    # 3. Valida JWT Token via Authorization Header (Bearer Token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        from app.core.auth import SECRET_KEY, ALGORITHM
        from jose import jwt, JWTError
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("sub"):
                return token
        except JWTError:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail='Credenciais inválidas ou sessão expirada. Forneça um X-API-Key válido ou Bearer JWT.'
    )

WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'webhook-secret-123')
