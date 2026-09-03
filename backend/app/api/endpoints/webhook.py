import logging
import os
import secrets
import urllib.parse

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.security import APIKeyQuery

from app.core.limiter import limiter
from app.core.security import WEBHOOK_SECRET

logger = logging.getLogger(__name__)
router = APIRouter()
api_key_query = APIKeyQuery(name="token", auto_error=False)
MAX_WEBHOOK_BYTES = 1_048_576


def verify_webhook_token(token: str = Security(api_key_query)):
    if not token or not secrets.compare_digest(token, WEBHOOK_SECRET):
        logger.warning("Tentativa de webhook negada")
        raise HTTPException(status_code=403, detail="Invalid Webhook Secret")
    return token


_redis_pool = None


async def get_redis_pool():
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        parsed = urllib.parse.urlparse(redis_url)
        database = int(parsed.path.strip("/") or 0)
        _redis_pool = await create_pool(
            RedisSettings(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                password=parsed.password,
                database=database,
            )
        )
    return _redis_pool


@router.post("/evolution")
@limiter.limit("60/minute")
async def evolution_webhook(request: Request, token: str = Security(verify_webhook_token)):
    """Receives Evolution API events without exposing payloads or internal errors."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Webhook payload too large")

    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Invalid webhook payload")
        logger.info("Webhook recebido: evento=%s", data.get("event", "unknown"))
        pool = await get_redis_pool()
        await pool.enqueue_job("process_message_job", data)
        return {"status": "ok"}
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except Exception:
        logger.exception("Falha ao processar webhook de forma segura")
        raise HTTPException(status_code=503, detail="Webhook temporariamente indisponível")
