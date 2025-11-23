from typing import List
from pydantic import BaseModel


class RagChatRequest(BaseModel):
  question: str
  history: List[str] = []


class RagChatResponse(BaseModel):
  answer: str
  contexts: List[str]
