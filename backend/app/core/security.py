from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
import os
import secrets

API_KEY_NAME = 'X-API-Key'
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', 'dev-secret-key-123')

async def get_api_key(request: Request, key: str = Security(api_key_header)):
    # Permite upgrade de WebSocket ou requisições autenticadas
    if request.scope.get("type") == "websocket":
        return None
        
    if key and secrets.compare_digest(key, INTERNAL_API_KEY):
        return key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials')

WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'webhook-secret-123')
