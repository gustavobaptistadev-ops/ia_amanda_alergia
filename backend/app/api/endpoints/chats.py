from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.chat import Contact, Message
from app.services.evolution_api import send_text_message
from pydantic import BaseModel
from typing import List
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

from pydantic import BaseModel, Field

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
async def get_messages(phone_number: str, db: AsyncSession = Depends(get_db), x_tenant_id: str = Header(None)):
    """Retorna as mensagens de um contato"""
    query = select(Message).join(Contact).where(Contact.phone_number == phone_number)
    if x_tenant_id:
        query = query.where(Contact.tenant_id == x_tenant_id)
        
    result = await db.execute(query.order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    return messages

@router.delete("/reset-all")
async def reset_all_conversations(db: AsyncSession = Depends(get_db)):
    """Reseta e limpa absolutamente todas as conversas, contatos e checkpoints de memoria do LangGraph."""
    from sqlalchemy import delete, text
    try:
        await db.execute(delete(Message))
        await db.execute(delete(Contact))
        
        try:
            await db.execute(text("DELETE FROM checkpoints"))
            await db.execute(text("DELETE FROM checkpoint_blobs"))
            await db.execute(text("DELETE FROM checkpoint_writes"))
        except Exception:
            pass
            
        await db.commit()
        await manager.broadcast("update")
        return {"status": "ok", "message": "Todas as conversas e memórias da IA foram completamente resetadas!"}
    except Exception as e:
        logger.error(f"Erro ao resetar todas as conversas: {e}")
        return {"status": "error", "detail": str(e)}

@router.delete("/{phone_number}/reset")
async def reset_conversation(phone_number: str, db: AsyncSession = Depends(get_db), x_tenant_id: str = Header(None)):
    """Reseta todo o histórico e memória de um contato (PostgreSQL + Checkpoints LangGraph)"""
    query = select(Contact).where(Contact.phone_number == phone_number)
    if x_tenant_id:
        query = query.where(Contact.tenant_id == x_tenant_id)
        
    result = await db.execute(query)
    contact = result.scalars().first()
    if contact:
        from sqlalchemy import delete, text
        # 1. Apaga todas as mensagens desse contato no banco relacional
        await db.execute(delete(Message).where(Message.contact_id == contact.id))
        
        # 2. Reseta o contato para estágio inicial e ativa o bot
        contact.stage = "novo_contato"
        contact.bot_active = True
        await db.commit()
        
        # 3. Limpa a memória de estado/checkpoints do LangGraph no Postgres para este thread_id (phone_number)
        try:
            await db.execute(text("DELETE FROM checkpoints WHERE thread_id = :tid"), {"tid": phone_number})
            await db.execute(text("DELETE FROM checkpoint_blobs WHERE thread_id = :tid"), {"tid": phone_number})
            await db.execute(text("DELETE FROM checkpoint_writes WHERE thread_id = :tid"), {"tid": phone_number})
            await db.commit()
        except Exception as e:
            # Caso as tabelas ainda não existam ou erro pontual
            pass
        
        # Notifica o frontend via websocket
        await manager.broadcast("update")
        
        return {"status": "ok", "message": "Conversa e memória da IA resetadas com sucesso!"}
    return {"status": "error", "message": "Contato não encontrado"}

@router.post("/{phone_number}/toggle_bot")
async def toggle_bot(phone_number: str, db: AsyncSession = Depends(get_db), x_tenant_id: str = Header(None)):
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

from app.core.limiter import limiter
from app.core.validators import sanitize_html
from fastapi import Request

@router.post("/{phone_number}/send")
@limiter.limit("30/minute")
async def send_human_message(request: Request, phone_number: str, payload: SendMessageRequest, db: AsyncSession = Depends(get_db), x_tenant_id: str = Header(None)):
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
        msg = Message(
            contact_id=contact.id,
            text=clean_text,
            sender='humano'
        )
        db.add(msg)
        # Transição transparente: Atendente assumiu a conversa, pausa o bot temporariamente
        contact.bot_active = False
        await db.commit()
        await manager.broadcast("update")
        
    return {"status": "ok", "bot_active": False}
