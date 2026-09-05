import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base


class LearningStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LearningSuggestion(Base):
    __tablename__ = "learning_suggestions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id = Column(
        String, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True
    )
    patient_name = Column(String(255), nullable=True)
    patient_phone = Column(String(50), nullable=True)
    suggestion_text = Column(Text, nullable=False)
    context = Column(Text, nullable=False)
    status = Column(
        SQLEnum(LearningStatus), default=LearningStatus.PENDING, nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    contact = relationship("Contact")
