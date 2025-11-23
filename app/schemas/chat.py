from typing import List, Literal, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
  role: Literal["user", "assistant", "system"]
  content: str


class ChatProfile(BaseModel):
  industry: Optional[str] = None
  employees: Optional[str] = None
  annual_sales_range: Optional[str] = None

class ChatChoice(BaseModel):
  id: str
  label: str


class HomeworkSuggestion(BaseModel):
  title: str
  detail: Optional[str] = None
  category: Optional[str] = None


class ChatRequest(BaseModel):
  messages: List[ChatMessage]
  profile: Optional[ChatProfile] = None
  document_ids: Optional[List[str]] = None
  conversation_id: Optional[str] = None
  user_id: Optional[str] = None


class ChatResponse(BaseModel):
  conversation_id: str
  message: str
  choices: List[ChatChoice]
  suggested_next_questions: Optional[List[str]] = None
  choice_options: Optional[List[str]] = None
  progress: Optional[int] = None
  homework_suggestions: Optional[List[HomeworkSuggestion]] = None
