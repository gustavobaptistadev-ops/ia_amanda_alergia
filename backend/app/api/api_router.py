from fastapi import APIRouter, Depends

from app.api.endpoints import (
    analytics,
    appointments,
    auth,
    calendar_public,
    chats,
    dashboard,
    evolution,
    logs,
    rag,
    settings,
    voice,
    webhook,
)
from app.core.security import get_api_key

api_router = APIRouter()

# Webhook e Auth ficam expostos para login e eventos
api_router.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
api_router.include_router(
    calendar_public.router, prefix="/calendar", tags=["Calendar Link"]
)
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação & RBAC"])

# Rotas de Voz (Twilio e WebSockets) - públicas para o gateway
api_router.include_router(voice.router, prefix="/voice", tags=["Voice Agent"])

# Demais rotas protegidas pelo INTERNAL_API_KEY
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_api_key)],
)
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics de Saúde"],
    dependencies=[Depends(get_api_key)],
)
api_router.include_router(
    appointments.router,
    prefix="/appointments",
    tags=["Agenda Médica"],
    dependencies=[Depends(get_api_key)],
)
api_router.include_router(
    evolution.router,
    prefix="/evolution",
    tags=["Evolution API"],
    dependencies=[Depends(get_api_key)],
)
api_router.include_router(
    chats.router,
    prefix="/chats",
    tags=["Chats Omnichannel"],
    dependencies=[Depends(get_api_key)],
)
api_router.include_router(
    rag.router,
    prefix="/rag",
    tags=["RAG (Base de Conhecimento)"],
    dependencies=[Depends(get_api_key)],
)
api_router.include_router(
    settings.router,
    prefix="/settings",
    tags=["Configurações de IA"],
    dependencies=[Depends(get_api_key)],
)
api_router.include_router(
    logs.router,
    prefix="/logs",
    tags=["Auditoria & Monitor de Lotes"],
    dependencies=[Depends(get_api_key)],
)
from app.api.endpoints import learning

api_router.include_router(
    learning.router,
    prefix="/learning",
    tags=["Aprendizado da IA"],
    dependencies=[Depends(get_api_key)],
)
