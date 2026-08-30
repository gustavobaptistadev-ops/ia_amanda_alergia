import logging
import collections
from datetime import datetime

# Buffer circular em memória com os últimos 200 logs ao vivo do servidor
_log_buffer = collections.deque(maxlen=200)

class InMemoryLogHandler(logging.Handler):
    """Captura todos os logs do Python e guarda em memória para streaming no painel."""
    def emit(self, record):
        try:
            msg = self.format(record)
            _log_buffer.append({
                "time": datetime.utcnow().strftime("%H:%M:%S"),
                "level": record.levelname,
                "name": record.name,
                "msg": msg
            })
        except Exception:
            pass

def get_live_logs():
    return list(_log_buffer)

def append_custom_log(level: str, name: str, msg: str):
    _log_buffer.append({
        "time": datetime.utcnow().strftime("%H:%M:%S"),
        "level": level,
        "name": name,
        "msg": msg
    })
