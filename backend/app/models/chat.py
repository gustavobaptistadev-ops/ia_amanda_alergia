from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String, unique=True, index=True, nullable=False) # The JID
    name = Column(String, nullable=True)
    bot_active = Column(Boolean, default=True) # Se a IA deve responder automaticamente
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id = Column(String, ForeignKey("contacts.id"), nullable=False)
    text = Column(Text, nullable=False)
    sender = Column(String, nullable=False) # 'paciente', 'ia', 'humano'
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="messages")
