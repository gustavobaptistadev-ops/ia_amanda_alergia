from fastapi import APIRouter
from app.api.endpoints import webhook, dashboard, evolution, chats, rag

api_router = APIRouter()

api_router.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(evolution.router, prefix="/evolution", tags=["Evolution API"])
api_router.include_router(chats.router, prefix="/chats", tags=["Chats Omnichannel"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG (Base de Conhecimento)"])
