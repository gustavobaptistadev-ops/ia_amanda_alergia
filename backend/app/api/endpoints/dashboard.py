from fastapi import APIRouter
from pydantic import BaseModel
import redis.asyncio as redis
import os
import json

router = APIRouter()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class DashboardStats(BaseModel):
    novos_contatos: int
    agendamentos: int
    em_atendimento: int

@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    """Retorna as estatísticas para o dashboard."""
    # Como a memória está no Redis (LangGraph), poderíamos contar as threads ativas.
    # Por enquanto, retornaremos dados simulados + contagem real se possível.
    try:
        async with redis.Redis.from_url(REDIS_URL) as r:
            # Busca todas as chaves de thread do langgraph no redis (ex: thread:*)
            keys = await r.keys("checkpoint*")
            contatos = len(keys) // 2 # Aproximação de threads
    except:
        contatos = 12

    return {
        "novos_contatos": contatos if contatos > 0 else 24,
        "agendamentos": 8,
        "em_atendimento": 3
    }

@router.get("/conversations")
async def get_conversations():
    """Retorna o histórico de conversas ativas."""
    # Retorna uma estrutura compatível com a tela de monitoramento.
    return [
        {"id": "1", "name": "Carlos Silva", "last_message": "Vou olhar minha agenda...", "time": "10:41", "status": "IA"},
        {"id": "2", "name": "Fernanda Lima", "last_message": "Qual o valor da consulta?", "time": "10:35", "status": "IA"},
        {"id": "3", "name": "João Pedro", "last_message": "Obrigado, marcarei depois.", "time": "09:15", "status": "Finalizado"}
    ]

@router.get("/kanban")
async def get_kanban_patients():
    """Retorna a lista de pacientes dividida nas colunas do Kanban."""
    return [
        {"title": "Novo Contato (IA)", "color": "bg-blue-500", "patients": ["Carlos Silva", "Fernanda Lima"]},
        {"title": "Em Anamnese", "color": "bg-amber-500", "patients": ["João Pedro"]},
        {"title": "Agendado", "color": "bg-emerald-500", "patients": ["Maria Oliveira", "Roberto Souza", "Ana Costa"]},
        {"title": "Atendimento Humano", "color": "bg-rose-500", "patients": []}
    ]
