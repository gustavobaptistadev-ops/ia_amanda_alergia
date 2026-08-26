from fastapi import APIRouter
from app.api.endpoints import webhook, dashboard, evolution

api_router = APIRouter()

api_router.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(evolution.router, prefix="/evolution", tags=["Evolution API"])

