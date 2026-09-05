"""Ponto de entrada da API e gerenciamento do ciclo de vida do serviÃ§o."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_router import api_router
from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.live_logger import InMemoryLogHandler
from app.core.logger_filter import PIIMaskingFilter
from app.database import Base, engine
from app.services.evolution_api import auto_create_instance, get_headers
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()
memory_handler = InMemoryLogHandler()
memory_handler.addFilter(PIIMaskingFilter())
root_logger.addHandler(memory_handler)

# Adiciona o filtro PII em todos os handlers do root
for handler in root_logger.handlers:
    handler.addFilter(PIIMaskingFilter())

# Injeta explicitamente nos loggers do Uvicorn para que os logs de acesso e erros HTTP apareÃ§am no painel
for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    uvicorn_logger = logging.getLogger(logger_name)
    uvicorn_logger.addHandler(memory_handler)
    for handler in uvicorn_logger.handlers:
        handler.addFilter(PIIMaskingFilter())

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos, migraÃ§Ãµes e integraÃ§Ãµes antes de aceitar trÃ¡fego."""
    logger.info("Iniciando aplicaÃ§Ã£o e sincronizando tabelas/colunas...")

    # 1. Garante que tabelas novas sejam criadas (usar alembic para colunas)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tabelas sincronizadas no PostgreSQL com sucesso.")

    # IngestÃ£o de RAG foi movida para o script standalone `backend/scripts/seed_rag.py`

    # Auto-create the instance in Evolution GO using the Global Key
    await auto_create_instance()

    yield
    # Cleanup se necessÃ¡rio


app = FastAPI(
    title="IA Amanda - RecepÃ§Ã£o Inteligente",
    description="API do sistema de recepÃ§Ã£o via WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

cors_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

# ConfiguraÃ§Ã£o de CORS para o painel de controle (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

from starlette.requests import Request
from starlette.responses import Response
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Adiciona cabeÃ§alhos de seguranÃ§a a cada resposta HTTP."""
    """Injeta headers de seguranÃ§a nÃ­vel bancÃ¡rio/militar em todas as respostas HTTP."""
    response: Response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https: wss: ws:; "
        "font-src 'self' data: https:; "
        "frame-ancestors 'none';"
    )
    return response


@app.get("/")
async def root():
    return {"message": "Bem-vindo Ã  API da IA Amanda - Sistema de RecepÃ§Ã£o Inteligente"}


@app.get("/health")
async def health_check():
    """Verifica dependÃªncias crÃ­ticas sem expor segredos ou dados sensÃ­veis."""
    """Health Check enriquecido â€” verifica todos os componentes crÃ­ticos do sistema."""
    import httpx
    import redis.asyncio as _redis
    from sqlalchemy import text as _text

    from app.database import engine as _engine

    status = {"status": "ok", "components": {}}

    # 1. Banco de dados PostgreSQL
    try:
        async with _engine.connect() as conn:
            await conn.execute(_text("SELECT 1"))
        status["components"]["database"] = "healthy"
    except Exception:
        status["components"]["database"] = "unhealthy"
        status["status"] = "degraded"

    # 2. Redis
    try:
        redis_url = settings.REDIS_URL
        async with _redis.Redis.from_url(redis_url) as r:
            await r.ping()
        status["components"]["redis"] = "healthy"
    except Exception:
        status["components"]["redis"] = "unhealthy"
        status["status"] = "degraded"

    # 3. Evolution API
    try:
        evolution_url = settings.EVOLUTION_API_URL
        if evolution_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{evolution_url}/instance/status",
                    headers=get_headers(),
                )
            status["components"]["evolution_api"] = (
                "healthy" if r.status_code == 200 else "unhealthy"
            )
            if r.status_code != 200:
                status["status"] = "degraded"
        else:
            status["components"]["evolution_api"] = "not_configured"
    except Exception:
        status["components"]["evolution_api"] = "unhealthy"
        status["status"] = "degraded"

    # 4. OpenAI API
    try:
        openai_key = settings.OPENAI_API_KEY
        status["components"]["openai"] = "configured" if openai_key else "not_configured"
    except Exception:
        status["components"]["openai"] = "unknown"

    return status


# InclusÃ£o das rotas da API
app.include_router(api_router, prefix="/api/v1")
