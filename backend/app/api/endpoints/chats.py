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

class SendMessageRequest(BaseModel):
    text: str

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
async def get_messages(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Retorna as mensagens de um contato"""
    result = await db.execute(
        select(Message)
        .join(Contact)
        .where(Contact.phone_number == phone_number)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return messages

@router.delete("/{phone_number}/reset")
async def reset_conversation(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Reseta todo o histórico e memória de um contato"""
    result = await db.execute(select(Contact).where(Contact.phone_number == phone_number))
    contact = result.scalar_one_or_none()
    if contact:
        from sqlalchemy import delete
        # Apaga todas as mensagens desse contato no banco relacional
        await db.execute(delete(Message).where(Message.contact_id == contact.id))
        
        # Reseta o contato para estágio inicial e ativa o bot
        contact.stage = "novo_contato"
        contact.bot_active = True
        await db.commit()
        
        # A memória do LangGraph agora é puxada dinamicamente do banco de dados (que acabamos de deletar),
        # então não há necessidade de limpar cache em memória!
        
        return {"status": "ok", "message": "Conversa resetada"}
    return {"status": "error", "message": "Contato não encontrado"}

@router.post("/{phone_number}/toggle_bot")
async def toggle_bot(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Alterna o status do bot para este contato"""
    result = await db.execute(select(Contact).where(Contact.phone_number == phone_number))
    contact = result.scalar_one_or_none()
    if contact:
        contact.bot_active = not contact.bot_active
        await db.commit()
        return {"status": "ok", "bot_active": contact.bot_active}
    return {"status": "error", "message": "Contato não encontrado"}

@router.post("/{phone_number}/send")
async def send_human_message(phone_number: str, request: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """Envia uma mensagem humana (atendente) e salva no banco"""
    await send_text_message(phone_number, request.text)
    
    # Save to db
    result = await db.execute(select(Contact).where(Contact.phone_number == phone_number))
    contact = result.scalar_one_or_none()
    if contact:
        msg = Message(
            contact_id=contact.id,
            text=request.text,
            sender='humano'
        )
        db.add(msg)
        await db.commit()
        
    return {"status": "ok"}
