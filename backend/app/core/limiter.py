import os

import redis.asyncio as redis_lib
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

redis_url = settings.REDIS_URL

# Limiter centralizado para rotas HTTP (por IP)
limiter = Limiter(
    key_func=get_remote_address, default_limits=["120/minute"], storage_uri=redis_url
)


async def check_phone_rate_limit(phone: str, max_per_minute: int = 20) -> bool:
    """
    Rate limiter por número de telefone via Redis (Sliding Window).
    Retorna True se o limite foi atingido (bloquear), False se está OK.
    O WhatsApp inteiro chega do mesmo IP — este limiter protege contra DDoS semântico por número.
    """
    if not phone:
        return False
    key = f"rate_limit:phone:{phone}"
    try:
        async with redis_lib.Redis.from_url(redis_url, decode_responses=True) as r:
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, 60)  # janela de 60 segundos
            return count > max_per_minute
    except Exception:
        return False  # fail-open: em caso de falha do Redis, não bloquear
