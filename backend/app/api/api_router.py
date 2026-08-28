from fastapi import APIRouter, Depends
from app.api.endpoints import webhook, dashboard, evolution, chats, rag
from app.core.security import get_api_key

api_router = APIRouter()

# Webhook fica exposto (usará outro método de validação via URL param ou body)
api_router.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])

# Demais rotas protegidas pelo INTERNAL_API_KEY
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(get_api_key)])
api_router.include_router(evolution.router, prefix="/evolution", tags=["Evolution API"], dependencies=[Depends(get_api_key)])
api_router.include_router(chats.router, prefix="/chats", tags=["Chats Omnichannel"], dependencies=[Depends(get_api_key)])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG (Base de Conhecimento)"], dependencies=[Depends(get_api_key)])
