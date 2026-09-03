"""Ponto de entrada da API e gerenciamento do ciclo de vida do serviço."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_router import api_router
from app.database import engine, Base
import logging
from app.services.evolution_api import auto_create_instance, get_headers
from contextlib import asynccontextmanager

from app.core.limiter import limiter, RateLimitExceeded, _rate_limit_exceeded_handler
from app.core.logger_filter import PIIMaskingFilter
from app.core.live_logger import InMemoryLogHandler, append_custom_log

logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()
memory_handler = InMemoryLogHandler()
memory_handler.addFilter(PIIMaskingFilter())
root_logger.addHandler(memory_handler)

# Adiciona o filtro PII em todos os handlers do root
for handler in root_logger.handlers:
    handler.addFilter(PIIMaskingFilter())

# Injeta explicitamente nos loggers do Uvicorn para que os logs de acesso e erros HTTP apareçam no painel
for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    l = logging.getLogger(logger_name)
    l.addHandler(memory_handler)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos, migrações e integrações antes de aceitar tráfego."""
    logger.info("Iniciando aplicação e sincronizando tabelas/colunas...")
    
    # 1. Garante que tabelas novas (system_logs, users, etc) sejam criadas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # 2. Executa DDL idempotente comando a comando (exigência do driver asyncpg)
        from sqlalchemy import text
        ddl_statements = [
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_operator VARCHAR;",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_card_number VARCHAR;",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_plan_name VARCHAR;",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_coverage VARCHAR;",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_accommodation VARCHAR;",
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS prep_reminder_sent BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS follow_up_sent BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reschedule_count INTEGER DEFAULT 0;",
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS google_event_id VARCHAR;",
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR;",
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS nps_sent BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS nps_score INTEGER;"
        ]
        for stmt in ddl_statements:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                logger.warning(f"Aviso ao executar DDL '{stmt}': {e}")
        logger.info("Tabelas e colunas sincronizadas no PostgreSQL com sucesso.")
    
    # Ingestão de RAG no startup se existir OPENAI_API_KEY
    import os, glob
    from app.core.rag import ingest_docs
    if os.getenv("OPENAI_API_KEY"):
        logger.info("Iniciando ingestão da base de conhecimento (RAG)...")
        kb_dir = os.path.join(os.path.dirname(__file__), '../docs/knowledge_base')
        try:
            for file in glob.glob(os.path.join(kb_dir, '*.md')):
                ingest_docs(file)
            logger.info("Ingestão de RAG concluída no startup.")
        except Exception as e:
            logger.error(f"Erro na ingestão de RAG: {e}")
    
    # Auto-create the instance in Evolution GO using the Global Key
    await auto_create_instance()
    
    yield
    # Cleanup se necessário

app = FastAPI(
    title="IA Amanda - Recepção Inteligente",
    description="API do sistema de recepção via WhatsApp",
    version="1.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

import os
frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "https://ia-amanda-frontend.up.railway.app")
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", frontend_url).split(",") if origin.strip()]

# Configuração de CORS para o painel de controle (Next.js)
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
    """Adiciona cabeçalhos de segurança a cada resposta HTTP."""
    """Injeta headers de segurança nível bancário/militar em todas as respostas HTTP."""
    response: Response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
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
    return {"message": "Bem-vindo à API da IA Amanda - Sistema de Recepção Inteligente"}

@app.get("/health")
async def health_check():
    """Verifica dependências críticas sem expor segredos ou dados sensíveis."""
    """Health Check enriquecido — verifica todos os componentes críticos do sistema."""
    import httpx
    import redis.asyncio as _redis
    from app.database import engine as _engine
    from sqlalchemy import text as _text

    status = {"status": "ok", "components": {}}

    # 1. Banco de dados PostgreSQL
    try:
        async with _engine.connect() as conn:
            await conn.execute(_text("SELECT 1"))
        status["components"]["database"] = "healthy"
    except Exception as e:
        status["components"]["database"] = "unhealthy"
        status["status"] = "degraded"

    # 2. Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        async with _redis.Redis.from_url(redis_url) as r:
            await r.ping()
        status["components"]["redis"] = "healthy"
    except Exception as e:
        status["components"]["redis"] = "unhealthy"
        status["status"] = "degraded"

    # 3. Evolution API
    try:
        evolution_url = os.getenv("EVOLUTION_API_URL", "")
        if evolution_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{evolution_url}/instance/status",
                    headers=get_headers(),
                )
            status["components"]["evolution_api"] = "healthy" if r.status_code == 200 else "unhealthy"
            if r.status_code != 200:
                status["status"] = "degraded"
        else:
            status["components"]["evolution_api"] = "not_configured"
    except Exception as e:
        status["components"]["evolution_api"] = "unhealthy"
        status["status"] = "degraded"

    # 4. OpenAI API
    try:
        openai_key = os.getenv("OPENAI_API_KEY", "")
        status["components"]["openai"] = "configured" if openai_key else "not_configured"
    except Exception:
        status["components"]["openai"] = "unknown"

    return status

# Inclusão das rotas da API
app.include_router(api_router, prefix="/api/v1")
