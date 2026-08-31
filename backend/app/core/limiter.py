import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Limiter centralizado para evitar importação circular entre main.py e endpoints
# Utiliza REDIS_URL para rate limiting distribuído real (Horizontal Scaling)
limiter = Limiter(
    key_func=get_remote_address, 
    default_limits=["120/minute"],
    storage_uri=redis_url
)
