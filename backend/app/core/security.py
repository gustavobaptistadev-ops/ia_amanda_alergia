from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os

API_KEY_NAME = 'X-API-Key'
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', 'dev-secret-key-123')

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == INTERNAL_API_KEY:
        return api_key_header
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials')

WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'webhook-secret-123')
