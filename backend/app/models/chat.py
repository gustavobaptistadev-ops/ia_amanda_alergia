from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'phone_number', name='uq_tenant_phone'),
    )
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=True) # nullable temporariamente para não quebrar dados antigos
    phone_number = Column(String, index=True, nullable=False) # The JID
    name = Column(String, nullable=True)
    bot_active = Column(Boolean, default=True) # Se a IA deve responder automaticamente
    stage = Column(String, default="novo_contato") # 'novo_contato', 'em_andamento', 'agendado'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tenant = relationship("Tenant")

    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id = Column(String, ForeignKey("contacts.id"), index=True, nullable=False)
    text = Column(Text, nullable=False)
    sender = Column(String, nullable=False) # 'paciente', 'ia', 'humano'
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="messages")
