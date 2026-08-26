from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_router import api_router

app = FastAPI(
    title="IA Amanda - Recepção Inteligente",
    description="API do sistema de recepção via WhatsApp",
    version="1.0.0"
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
