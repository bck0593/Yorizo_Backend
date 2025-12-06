from pathlib import Path
import sys
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import models  # noqa: E402
import database  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_chat_tables():
    """conversations/messages テーブルを毎回リセットする。"""
    models.Base.metadata.drop_all(
        bind=database.engine,
        tables=[models.Conversation.__table__, models.Message.__table__],
    )
    models.Base.metadata.create_all(
        bind=database.engine,
        tables=[models.Conversation.__table__, models.Message.__table__],
    )
    db = database.SessionLocal()
    try:
        db.query(models.Message).delete()
        db.query(models.Conversation).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """LLM をモックした /api/chat 用 TestClient。"""
    sys.modules["models"] = models
    sys.modules["database"] = database

    from app.core import openai_client as backend_openai_client

    sys.modules["app.core.openai_client"] = backend_openai_client

    from main import app  # noqa: E402

    # chat_completion_json が「壊れた JSON」を返すようにモックする
    def _broken_chat_completion_json(messages, temperature=None, max_tokens=None) -> str:  # type: ignore[override]
        return "not-a-json"

    monkeypatch.setattr(backend_openai_client, "chat_completion_json", _broken_chat_completion_json)

    return TestClient(app)


def _post_chat(client: TestClient, payload: Dict[str, Any]):
    return client.post("/api/chat", json=payload)


def test_chat_fallback_keeps_response_shape(client: TestClient):
    """LLM が壊れた JSON を返しても、ChatTurnResponse の型を維持してフォールバックする。"""
    payload = {
        "user_id": "u-chat-fallback",
        "message": "はじめまして。最近、売上が伸びなくて不安です。",
    }
    resp = _post_chat(client, payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # 型（フィールド構成）が崩れていないこと
    assert set(data.keys()) == {
        "conversation_id",
        "reply",
        "question",
        "options",
        "cta_buttons",
        "allow_free_text",
        "step",
        "done",
    }

    # フォールバックメッセージであること
    assert "Yorizo が考えるのに失敗しました" in data["reply"]
    assert data["done"] is False
    assert isinstance(data["options"], list)
    assert isinstance(data.get("cta_buttons"), list) or data.get("cta_buttons") is None
    assert isinstance(data["allow_free_text"], bool)

