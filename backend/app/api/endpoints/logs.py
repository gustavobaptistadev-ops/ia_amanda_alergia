from pydantic import BaseModel
from datetime import datetime
from app.core.config import settings

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import AsyncSessionLocal, get_db
from app.models.chat import SystemLog
from app.services.reminder_service import check_and_send_reminders

router = APIRouter()
REDIS_URL = settings.REDIS_URL


async def record_system_log(
    category: str, level: str, title: str, detail: str | None = None
):
    """Função utilitária para gravar logs estruturados no banco de dados."""
    try:
        async with AsyncSessionLocal() as session:
            log_entry = SystemLog(
                category=category, level=level, title=title, detail=detail
            )
            session.add(log_entry)
            await session.commit()
    except Exception as e:
        print(f"Erro ao salvar SystemLog: {e}", flush=True)


@router.get("/")
async def list_system_logs(
    category: str | None = Query(None),
    level: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Lista os logs e eventos de auditoria do sistema em tempo real com fallback gracioso."""
    try:
        query = select(SystemLog)
        if category:
            query = query.where(SystemLog.category == category)
        if level:
            query = query.where(SystemLog.level == level)

        result = await db.execute(
            query.order_by(SystemLog.created_at.desc()).limit(limit)
        )
        logs = result.scalars().all()

        return [
            {
                "id": log_item.id,
                "category": log_item.category,
                "level": log_item.level,
                "title": log_item.title,
                "detail": log_item.detail,
                "created_at": log_item.created_at.strftime("%d/%m/%Y %H:%M:%S")
                if log_item.created_at
                else None,
            }
            for log_item in logs
        ]
    except Exception as e:
        print(
            f"Aviso: Erro ao listar system_logs (sincronizando tabela): {e}", flush=True
        )
        return []


@router.get("/live")
async def get_live_terminal_logs():
    """Retorna os logs brutos e vivos do console em tempo real."""
    from app.core.live_logger import get_live_logs

    return get_live_logs()




class ClientLogPayload(BaseModel):
    level: str = "INFO"
    name: str = "Frontend"
    msg: str


@router.post("/client")
async def receive_client_log(payload: ClientLogPayload):
    """Permite que o frontend envie seus logs para o terminal."""
    from app.core.live_logger import append_custom_log

    append_custom_log(payload.level, f"Frontend:{payload.name}", payload.msg)
    return {"status": "ok"}


@router.get("/worker-stats")
async def get_worker_stats():
    """Retorna a saúde do Redis e dos lotes em background."""
    stats = {
        "status": "online",
        "redis_connected": False,
        "active_keys": 0,
        "last_batch_run": None,
        "now": datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S UTC"),
    }
    try:
        async with redis.Redis.from_url(REDIS_URL) as r:
            await r.ping()
            stats["redis_connected"] = True
            keys = await r.keys("*")
            stats["active_keys"] = len(keys)
    except Exception as e:
        stats["redis_connected"] = False
        stats["error"] = str(e)

    return stats


@router.post("/trigger-reminders")
async def trigger_reminders_manually():
    """Permite forçar a execução imediata do lote de lembretes."""
    try:
        await check_and_send_reminders()
        await record_system_log(
            category="cron_lembretes",
            level="SUCCESS",
            title="Lote de lembretes executado manualmente",
            detail="Disparo sob demanda solicitado via Painel Web.",
        )
        return {
            "status": "ok",
            "message": "Lote executado",
        }
    except Exception as e:
        await record_system_log(
            category="cron_lembretes",
            level="ERROR",
            title="Falha ao executar lote manual",
            detail=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))
