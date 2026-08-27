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

@router.get("/")
async def get_chats(db: AsyncSession = Depends(get_db)):
    """Retorna a lista de contatos ordenados pela última mensagem"""
    # Simple query for now
    result = await db.execute(select(Contact).order_by(Contact.updated_at.desc()))
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
