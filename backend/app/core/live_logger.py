import logging
import json
import os
import redis
from datetime import datetime

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Cliente síncrono para o handler
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

LOG_KEY = "live_logs_buffer"

class InMemoryLogHandler(logging.Handler):
    """Captura todos os logs do Python e guarda no Redis para streaming centralizado no painel."""
    def emit(self, record):
        try:
            msg = self.format(record)
            log_entry = {
                "time": datetime.utcnow().strftime("%H:%M:%S"),
                "level": record.levelname,
                "name": record.name,
                "msg": msg
            }
            redis_client.lpush(LOG_KEY, json.dumps(log_entry))
            redis_client.ltrim(LOG_KEY, 0, 199)
        except Exception:
            pass

def get_live_logs():
    try:
        raw_logs = redis_client.lrange(LOG_KEY, 0, -1)
        # O lpush empilha no inicio (index 0). Para visualizar na ordem correta, reverte a lista
        return [json.loads(r) for r in reversed(raw_logs)]
    except Exception:
        return []

def append_custom_log(level: str, name: str, msg: str):
    log_entry = {
        "time": datetime.utcnow().strftime("%H:%M:%S"),
        "level": level,
        "name": name,
        "msg": msg
    }
    try:
        redis_client.lpush(LOG_KEY, json.dumps(log_entry))
        redis_client.ltrim(LOG_KEY, 0, 199)
    except Exception:
        pass

