from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from app.models.base import GUID_TYPE, default_uuid, utcnow
from app.models.enums import ConversationStatus

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.memory import HomeworkTask
    from app.models.document import Document


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(GUID_TYPE, primary_key=True, default=default_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(GUID_TYPE, ForeignKey("users.id"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    main_concern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="chat")
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=ConversationStatus.IN_PROGRESS.value)
    step: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    memo: Mapped[Optional["ConsultationMemo"]] = relationship(
        "ConsultationMemo", back_populates="conversation", uselist=False, cascade="all, delete-orphan"
    )
    homework_tasks: Mapped[List["HomeworkTask"]] = relationship(
        "HomeworkTask", back_populates="conversation", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(GUID_TYPE, primary_key=True, default=default_uuid)
    conversation_id: Mapped[str] = mapped_column(GUID_TYPE, ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


class ConsultationMemo(Base):
    __tablename__ = "consultation_memos"

    id: Mapped[str] = mapped_column(GUID_TYPE, primary_key=True, default=default_uuid)
    conversation_id: Mapped[str] = mapped_column(
        GUID_TYPE, ForeignKey("conversations.id"), nullable=False, unique=True
    )
    current_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    important_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="memo")


__all__ = ["Conversation", "Message", "ConsultationMemo"]
