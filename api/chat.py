import json
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.openai_client import generate_guided_reply
from app.schemas.chat import ChatRequest, ChatResponse
from database import get_db
from models import CompanyProfile, Conversation, Document, Memory, Message, User, HomeworkTask

router = APIRouter()
logger = logging.getLogger(__name__)


def _ensure_user(db: Session, user_id: str | None) -> User | None:
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, nickname="guest")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _get_or_create_conversation(db: Session, conversation_id: str | None, user: User | None) -> Conversation:
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            return conv
    conv = Conversation(
        user_id=user.id if user else None,
        started_at=datetime.utcnow(),
        channel="chat",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _persist_messages(db: Session, conversation: Conversation, messages: List[dict]) -> None:
    for m in messages:
        if m["role"] not in {"user", "assistant", "system"}:
            continue
        msg = Message(
            conversation_id=conversation.id,
            role=m["role"],
            content=m["content"],
            created_at=datetime.utcnow(),
        )
        db.add(msg)
    db.commit()


def _load_context(db: Session, user: User | None) -> str:
    if not user:
        return ""

    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).first()
    memory = db.query(Memory).filter(Memory.user_id == user.id).first()

    profile_lines = [
        f"- 会社名: {profile.company_name or '未登録'}" if profile else "- 会社名: 未登録",
        f"- 業種: {profile.industry or '未登録'}" if profile else "- 業種: 未登録",
        f"- 従業員数: {profile.employees_range or '未登録'}" if profile else "- 従業員数: 未登録",
        f"- 年商レンジ: {profile.annual_sales_range or '未登録'}" if profile else "- 年商レンジ: 未登録",
        f"- 所在地: {profile.location_prefecture or '未登録'}" if profile else "- 所在地: 未登録",
        f"- 創業年数: {profile.years_in_business or '未登録'}" if profile else "- 創業年数: 未登録",
    ]

    remembered: list[str] = []
    if memory and memory.remembered_facts:
        try:
            parsed = json.loads(memory.remembered_facts)
            if isinstance(parsed, list):
                remembered = [str(x) for x in parsed]
        except Exception:
            remembered = (
                memory.remembered_facts.split("\n")
                if "\n" in memory.remembered_facts
                else [memory.remembered_facts]
            )

    persona_prompt = (
        "あなたは日本の『中小企業診断士』資格を持つ経営コンサルタントです。\n"
        "相談者は従業員数1〜20名程度の小規模事業者・個人事業主です。\n"
        "相談者の気持ちに寄り添いながら、質問を重ねて本質的な経営課題を一緒に言語化し、"
        "会社の強み・弱み・今やるべき具体的な一歩を整理してください。\n"
        "上から目線ではなく、パートナーとして伴走する口調で話します。\n\n"
        "会社の基本情報:\n"
        f"{chr(10).join(profile_lines)}\n\n"
        "Yorizoがこれまでに覚えていること（あれば）:\n"
        + ("\n".join(remembered) if remembered else "（まだ記録がありません）")
        + "\n\n"
        "いきなり答えを言い切らず、共感しながら段階的に状況を整理してください。"
    )
    return persona_prompt


def _document_context(db: Session, document_ids: List[str] | None) -> str:
    if not document_ids:
        return ""
    docs = (
        db.query(Document)
        .filter(Document.id.in_(document_ids))
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    snippets = []
    for doc in docs:
        content = (doc.content_text or "")[:800]
        snippets.append(f"{doc.filename}:\n{content}")
    return "\n\n".join(snippets)


def _estimate_progress(messages: List[dict]) -> int:
    """
    Simple heuristic for diagnosis progress based on user turns.
    """
    user_turns = [m for m in messages if m.get("role") == "user"]
    count = len(user_turns)
    if count == 0:
        return 0
    if count == 1:
        return 30
    if count <= 3:
        return 60
    if count <= 5:
        return 80
    return 100


def _persist_homework_suggestions(
    db: Session,
    conversation: Conversation,
    user: User | None,
    suggestions: List[dict] | None,
) -> None:
    if not suggestions:
        return
    for item in suggestions:
        title = item.get("title")
        if not title:
            continue
        exists = (
            db.query(HomeworkTask)
            .filter(
                HomeworkTask.conversation_id == conversation.id,
                HomeworkTask.title == title,
            )
            .first()
        )
        if exists:
            continue
        task = HomeworkTask(
            user_id=user.id if user else "unknown",
            conversation_id=conversation.id,
            title=title,
            detail=item.get("detail"),
            category=item.get("category"),
            status="pending",
        )
        db.add(task)
    db.commit()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages is required")

    try:
        user = _ensure_user(db, payload.user_id)
        conversation = _get_or_create_conversation(db, payload.conversation_id, user)

        raw_messages = [m.model_dump() for m in payload.messages]
        latest_user_message = next((m for m in reversed(raw_messages) if m.get("role") == "user"), None)

        persona_prompt = _load_context(db, user)
        doc_context = _document_context(db, payload.document_ids)

        data = await generate_guided_reply(
            raw_messages,
            context=doc_context or None,
            system_prompt=persona_prompt,
        )

        assistant_message = {
            "role": "assistant",
            "content": data.get("message", ""),
        }

        if latest_user_message:
            _persist_messages(db, conversation, [latest_user_message])
            if not conversation.main_concern:
                conversation.main_concern = latest_user_message.get("content", "")[:200]
        _persist_messages(db, conversation, [assistant_message])
        _persist_homework_suggestions(db, conversation, user, data.get("homework_suggestions"))
        db.commit()

        progress = data.get("progress")
        if progress is None:
            progress = _estimate_progress(raw_messages)

        return ChatResponse(
            conversation_id=conversation.id,
            message=data.get("message", ""),
            choices=data.get("choices", []),
            suggested_next_questions=data.get("suggested_next_questions") or [],
            choice_options=data.get("choice_options") or [],
            progress=progress,
            homework_suggestions=data.get("homework_suggestions") or [],
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("chat_endpoint failed")
        raise HTTPException(status_code=500, detail="Chat error") from exc
