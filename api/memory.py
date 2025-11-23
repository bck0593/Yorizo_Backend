import json
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Conversation, Memory, User


class PastConversation(BaseModel):
    id: str
    title: str
    date: str


class MemoryResponse(BaseModel):
    current_concerns: list[str]
    important_points_for_expert: list[str]
    nickname: str
    remembered_facts: list[str]
    past_conversations: list[PastConversation]


router = APIRouter()


def _ensure_user(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, nickname="ゲスト")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _json_to_list(raw: str | None, fallback: list[str]) -> list[str]:
    if not raw:
        return fallback
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(item) for item in data]
    except Exception:
        pass
    return fallback


@router.get("/memory/{user_id}", response_model=MemoryResponse)
async def get_memory(user_id: str, db: Session = Depends(get_db)) -> MemoryResponse:
    user = _ensure_user(db, user_id)
    memory = db.query(Memory).filter(Memory.user_id == user.id).first()

    if not memory:
        memory = Memory(
            user_id=user.id,
            current_concerns=json.dumps(["原材料費の高騰で利益率が下がっている"], ensure_ascii=False),
            important_points=json.dumps(["ここ1年の粗利率の推移を専門家と確認したい"], ensure_ascii=False),
            remembered_facts=json.dumps(["福岡市で飲食店を経営している"], ensure_ascii=False),
            last_updated_at=datetime.utcnow(),
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)

    past = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.started_at.desc())
        .limit(10)
        .all()
    )
    past_conversations = [
        PastConversation(
            id=conv.id,
            title=conv.title or (conv.main_concern or "相談"),
            date=(conv.started_at or datetime.utcnow()).date().isoformat(),
        )
        for conv in past
    ]

    return MemoryResponse(
        current_concerns=_json_to_list(memory.current_concerns, []),
        important_points_for_expert=_json_to_list(memory.important_points, []),
        nickname=user.nickname or "ゲストさん",
        remembered_facts=_json_to_list(memory.remembered_facts, []),
        past_conversations=past_conversations,
    )
