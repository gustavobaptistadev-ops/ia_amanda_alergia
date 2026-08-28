from fastapi import APIRouter, Request, HTTPException, Security
from fastapi.security import APIKeyQuery
import logging
from arq import create_pool
from arq.connections import RedisSettings
import os
import urllib.parse
from app.core.security import WEBHOOK_SECRET

logger = logging.getLogger(__name__)
router = APIRouter()

api_key_query = APIKeyQuery(name="token", auto_error=False)

def verify_webhook_token(token: str = Security(api_key_query)):
    if token != WEBHOOK_SECRET:
        logger.warning(f"Tentativa de webhook negada. Token invalido: {token}")
        raise HTTPException(status_code=403, detail="Invalid Webhook Secret")
    return token

_redis_pool = None

async def get_redis_pool():
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        parsed = urllib.parse.urlparse(redis_url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        password = parsed.password
        database = int(parsed.path.replace('/', '')) if parsed.path and parsed.path != '/' else 0
        redis_settings = RedisSettings(host=host, port=port, password=password, database=database)
        _redis_pool = await create_pool(redis_settings)
    return _redis_pool

@router.post("/evolution")
async def evolution_webhook(request: Request, token: str = Security(verify_webhook_token)):
    """Webhook para receber eventos da EvolutionAPI / Ghosthub."""
    try:
        data = await request.json()
        print(f">>> [DEBUG] Webhook Payload: {data}", flush=True)
        
        pool = await get_redis_pool()
        await pool.enqueue_job("process_message_job", data)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Erro no webhook: {e}", flush=True)
        return {"status": "error", "message": str(e)}
