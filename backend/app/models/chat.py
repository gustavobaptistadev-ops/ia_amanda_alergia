from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Integer
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
    insurance_operator = Column(String, nullable=True) # Ex: Unimed, Bradesco, Amil, SulAmérica
    insurance_card_number = Column(String, nullable=True) # Matrícula do plano
    insurance_plan_name = Column(String, nullable=True) # Nome da categoria / plano
    insurance_coverage = Column(String, nullable=True) # Abrangência (Nacional, Estadual)
    insurance_accommodation = Column(String, nullable=True) # Apartamento, Enfermaria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tenant = relationship("Tenant")

    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="contact", cascade="all, delete-orphan")

from app.models.types import EncryptedText

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id = Column(String, ForeignKey("contacts.id"), index=True, nullable=False)
    text = Column(EncryptedText, nullable=False)
    sender = Column(String, nullable=False) # 'paciente', 'ia', 'humano'
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="messages")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id = Column(String, ForeignKey("contacts.id"), index=True, nullable=False)
    patient_name = Column(String, nullable=False)
    appointment_time = Column(DateTime, nullable=False, index=True)
    status = Column(String, default="agendado") # 'agendado', 'confirmado', 'cancelado', 'concluido'
    reminder_24h_sent = Column(Boolean, default=False)
    reminder_2h_sent = Column(Boolean, default=False)
    prep_reminder_sent = Column(Boolean, default=False) # Reforço de suspensão de antialérgicos 5 dias antes
    follow_up_sent = Column(Boolean, default=False) # Acolhimento 48h pós-consulta
    reschedule_count = Column(Integer, default=0) # Quantas vezes a consulta foi reagendada
    google_event_id = Column(String, nullable=True) # ID do evento no Google Calendar
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="appointments")

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String, nullable=False, index=True) # 'cron_lembretes', 'webhook', 'ia_amanda', 'sistema', 'seguranca'
    level = Column(String, default="INFO") # 'INFO', 'WARNING', 'ERROR', 'SUCCESS'
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
