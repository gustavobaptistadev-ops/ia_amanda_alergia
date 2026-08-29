from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Limiter centralizado para evitar importação circular entre main.py e endpoints
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
