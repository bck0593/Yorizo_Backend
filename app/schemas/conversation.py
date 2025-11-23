from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from app.schemas.homework import HomeworkTaskRead


class ConversationSummary(BaseModel):
    id: str
    title: str
    date: str

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    conversations: List[ConversationSummary]


class ConversationMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(BaseModel):
    id: str
    title: str
    started_at: datetime | None = None
    messages: List[ConversationMessage]

    model_config = ConfigDict(from_attributes=True)


class ConsultationMemoResponse(BaseModel):
    current_points: List[str]
    important_points: List[str]
    updated_at: datetime


class ConsultationMemoRequest(BaseModel):
    regenerate: bool = False


class ConversationReport(BaseModel):
    id: str
    title: str
    date: date
    summary: List[str]
    key_topics: List[str]
    homework: List[HomeworkTaskRead]

    model_config = ConfigDict(from_attributes=True)
