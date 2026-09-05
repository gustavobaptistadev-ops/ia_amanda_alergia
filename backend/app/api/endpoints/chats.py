from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import get_current_user
from app.core.security import get_api_key
from app.database import get_db
from app.models.chat import Contact, Message
from app.services.evolution_api import send_text_message

router = APIRouter()

import asyncio
import logging

import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

REDIS_URL = settings.REDIS_URL
PUBSUB_CHANNEL = "chat_updates"


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        self.listener_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Inicia a task de listen do Redis PubSub apenas se houver conexões locais ativas
        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(self._listen_to_redis())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def _listen_to_redis(self):
        """Task que escuta o PubSub do Redis e repassa aos WebSockets conectados neste worker Uvicorn"""
        try:
            await self.pubsub.subscribe(PUBSUB_CHANNEL)
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    payload = message["data"]
                    for connection in self.active_connections:
                        try:
                            await connection.send_text(payload)
                        except Exception:
                            # Ignora se a conexão já caiu, o loop de receive trata o disconnect
                            pass
        except Exception as e:
            logger.error(f"Erro no Redis PubSub Listener: {e}")

    async def broadcast(self, message: str):
        """Faz PUBLISH no Redis. Assim, qualquer Worker ou API Server pode sinalizar atualização global."""
        try:
            # Em vez de mandar apenas para `self.active_connections`, publica no Redis!
            pub_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            await pub_redis.publish(PUBSUB_CHANNEL, message)
            await pub_redis.aclose()
        except Exception as e:
            logger.error(f"Erro ao publicar no Redis PubSub: {e}")


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await get_api_key(websocket=websocket)
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


from pydantic import Field


class SendMessageRequest(BaseModel):
    text: str = Field(..., max_length=4096)


from fastapi import Header


@router.get("/")
async def get_chats(db: AsyncSession = Depends(get_db), x_tenant_id: str = Header(None)):
    """Retorna a lista de contatos ordenados pela última mensagem"""
    query = select(Contact)
    if x_tenant_id:
        query = query.where(Contact.tenant_id == x_tenant_id)

    result = await db.execute(query.order_by(Contact.updated_at.desc()))
    contacts = result.scalars().all()
    return contacts


@router.get("/{phone_number}/messages")
async def get_messages(
    phone_number: str, db: AsyncSession = Depends(get_db), x_tenant_id: str = Header(None)
):
    """Retorna as mensagens de um contato"""
    query = select(Message).join(Contact).where(Contact.phone_number == phone_number)
    if x_tenant_id:
        query = query.where(Contact.tenant_id == x_tenant_id)

    result = await db.execute(query.order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    return messages


@router.delete("/reset-all")
async def reset_all_conversations(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    """Reseta e limpa absolutamente todas as conversas, contatos e checkpoints de memoria do LangGraph."""
    from sqlalchemy import delete, text

    from app.models.chat import Appointment, Contact, Message

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem resetar todas as conversas.",
        )
    try:
        await db.execute(delete(Message))
        await db.execute(delete(Appointment))
        await db.execute(delete(Contact))

        try:
            await db.execute(text("DELETE FROM checkpoints"))
            await db.execute(text("DELETE FROM checkpoint_blobs"))
            await db.execute(text("DELETE FROM checkpoint_writes"))
        except Exception as checkpoint_error:
            logger.exception(
                "Falha ao limpar a memória persistente no reset global: %s",
                checkpoint_error,
            )
            await db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Não foi possível limpar a memória persistente das conversas.",
            )

        await db.commit()
        await manager.broadcast("update")
        return {
            "status": "ok",
            "message": "Todas as conversas e memórias da IA foram completamente resetadas!",
        }
    except Exception as e:
        logger.error(f"Erro ao resetar todas as conversas: {e}")
        return {"status": "error", "detail": str(e)}


@router.delete("/{phone_number}/reset")
async def reset_conversation(
    phone_number: str, db: AsyncSession = Depends(get_db), x_tenant_id: str = Header(None)
):
    """Reseta todo o histórico e memória de um contato (PostgreSQL + Checkpoints LangGraph)"""
    query = select(Contact).where(Contact.phone_number == phone_number)
    if x_tenant_id:
        query = query.where(Contact.tenant_id == x_tenant_id)

    result = await db.execute(query)
    contact = result.scalars().first()
    if contact:
        from sqlalchemy import delete, text

        from app.models.chat import Appointment, Message

        # 1. Apaga todas as mensagens e agendamentos desse contato
        await db.execute(delete(Message).where(Message.contact_id == contact.id))
        await db.execute(delete(Appointment).where(Appointment.contact_id == contact.id))

        # 2. Reseta o contato completamente para o estado inicial
        contact.stage = "novo_contato"
        contact.bot_active = True
        contact.name = None
        contact.insurance_operator = None
        contact.insurance_card_number = None
        contact.insurance_plan_name = None
        contact.insurance_coverage = None
        contact.insurance_accommodation = None
        await db.commit()

        # 3. Limpa a memória de estado/checkpoints do LangGraph no Postgres para este thread_id (phone_number)
        try:
            await db.execute(
                text("DELETE FROM checkpoints WHERE thread_id = :tid"),
                {"tid": phone_number},
            )
            await db.execute(
                text("DELETE FROM checkpoint_blobs WHERE thread_id = :tid"),
                {"tid": phone_number},
            )
            await db.execute(
                text("DELETE FROM checkpoint_writes WHERE thread_id = :tid"),
                {"tid": phone_number},
            )
            await db.commit()
        except Exception as checkpoint_error:
            logger.exception(
                "Falha ao limpar a memória persistente do contato %s: %s",
                phone_number[:6],
                checkpoint_error,
            )
            await db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Não foi possível limpar a memória persistente desta conversa.",
            )

        # Notifica o frontend via websocket
        await manager.broadcast("update")

        return {
            "status": "ok",
            "message": "Conversa e memória da IA resetadas com sucesso!",
        }
    return {"status": "error", "message": "Contato não encontrado"}


@router.post("/{phone_number}/toggle_bot")
async def toggle_bot(
    phone_number: str, db: AsyncSession = Depends(get_db), x_tenant_id: str = Header(None)
):
    """Alterna o status do bot para este contato"""
    query = select(Contact).where(Contact.phone_number == phone_number)
    if x_tenant_id:
        query = query.where(Contact.tenant_id == x_tenant_id)

    result = await db.execute(query)
    contact = result.scalars().first()
    if contact:
        contact.bot_active = not contact.bot_active
        await db.commit()
        return {"status": "ok", "bot_active": contact.bot_active}
    return {"status": "error", "message": "Contato não encontrado"}


from fastapi import Request

from app.core.limiter import limiter
from app.core.validators import sanitize_html


@router.post("/{phone_number}/send")
@limiter.limit("30/minute")
async def send_human_message(
    request: Request,
    phone_number: str,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    x_tenant_id: str = Header(None),
):
    """Envia uma mensagem humana (atendente) com sanitização anti-XSS, rate limiting e Human Takeover automático."""
    clean_text = sanitize_html(payload.text)
    await send_text_message(phone_number, clean_text)

    # Save to db
    query = select(Contact).where(Contact.phone_number == phone_number)
    if x_tenant_id:
        query = query.where(Contact.tenant_id == x_tenant_id)

    result = await db.execute(query)
    contact = result.scalars().first()
    if contact:
        msg = Message(contact_id=contact.id, text=clean_text, sender="humano")
        db.add(msg)
        # Transição transparente: Atendente assumiu a conversa, pausa o bot temporariamente
        # Transição transparente: Atendente assumiu a conversa, pausa o bot temporariamente
        contact.bot_active = False
        await db.commit()
        await manager.broadcast("update")

        # INJEÇÃO NA MEMÓRIA DO LANGGRAPH
        try:
            from langchain_core.messages import AIMessage

            from app.core.orchestrator import app_graph, init_checkpointer

            if app_graph is None:
                await init_checkpointer()
            # Injeta a mensagem humana como se fosse a IA falando (para manter a ilusão contextual)
            config = {"configurable": {"thread_id": phone_number}}
            msg_to_inject = AIMessage(
                content=f"*(Mensagem enviada por humano)*: {clean_text}"
            )
            await app_graph.aupdate_state(config, {"messages": [msg_to_inject]})
        except Exception as e:
            import logging

            logging.warning(
                f"Não foi possível atualizar a memória do LangGraph para {phone_number}: {e}"
            )

    return {"status": "ok", "bot_active": False}
