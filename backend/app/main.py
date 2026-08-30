from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_router import api_router
from app.database import engine, Base
import logging
from app.services.evolution_api import auto_create_instance
from contextlib import asynccontextmanager

from app.core.limiter import limiter, RateLimitExceeded, _rate_limit_exceeded_handler
from app.core.logger_filter import PIIMaskingFilter
from app.core.live_logger import InMemoryLogHandler, append_custom_log

logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()
memory_handler = InMemoryLogHandler()
memory_handler.addFilter(PIIMaskingFilter())
root_logger.addHandler(memory_handler)

for handler in root_logger.handlers:
    handler.addFilter(PIIMaskingFilter())

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
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
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS follow_up_sent BOOLEAN DEFAULT FALSE;"
        ]
        for stmt in ddl_statements:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                logger.warning(f"Aviso ao executar DDL '{stmt}': {e}")
        logger.info("Tabelas e colunas sincronizadas no PostgreSQL com sucesso.")
    
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

# Configuração de CORS para o painel de controle (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url, 
        "http://localhost:3000",
        "https://tranquil-encouragement-production-52cf.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

from starlette.requests import Request
from starlette.responses import Response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
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
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
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

# Inclusão das rotas da API
app.include_router(api_router, prefix="/api/v1")
