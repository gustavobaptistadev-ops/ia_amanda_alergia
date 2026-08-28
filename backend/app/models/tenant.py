from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False) # e.g. "Clínica Alergia Matriz"
    instance_name = Column(String, unique=True, index=True, nullable=False) # e.g. "ia_amanda"
    instance_token = Column(String, nullable=False) # API Key from evolution
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
