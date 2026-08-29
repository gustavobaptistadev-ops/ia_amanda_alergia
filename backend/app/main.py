from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_router import api_router
from app.database import engine, Base
import logging
from app.services.evolution_api import auto_create_instance
from contextlib import asynccontextmanager

from app.core.limiter import limiter, RateLimitExceeded, _rate_limit_exceeded_handler

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # As tabelas agora são gerenciadas via Alembic
    logger.info("Iniciando aplicação (Migrações via Alembic)...")
    
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
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Bem-vindo à API da IA Amanda - Sistema de Recepção Inteligente"}

# Inclusão das rotas da API
app.include_router(api_router, prefix="/api/v1")
