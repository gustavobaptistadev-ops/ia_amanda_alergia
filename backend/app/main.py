from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_router import api_router
from app.database import engine, Base
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar as tabelas do banco de dados no startup
    logger.info("Criando tabelas no banco de dados...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup se necessário

app = FastAPI(
    title="IA Amanda - Recepção Inteligente",
    description="API do sistema de recepção via WhatsApp",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração de CORS para o painel de controle (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Na produção, substituir pelo domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Bem-vindo à API da IA Amanda - Sistema de Recepção Inteligente"}

# Inclusão das rotas da API
app.include_router(api_router, prefix="/api/v1")
