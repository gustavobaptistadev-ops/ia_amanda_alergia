from fastapi import APIRouter
from app.api.endpoints import webhook, dashboard

api_router = APIRouter()

api_router.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
