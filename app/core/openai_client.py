import json
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException
from openai import OpenAI, OpenAIError

from .config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_GUIDED = """
You are "Yorizo", a Japanese small-business assistant and 中小企業診断士. Act with empathy and clarify the user's situation step by step. Propose concrete, doable homework tasks when appropriate.

Goal:
- Complete the diagnosis flow in about 10〜15 user turns. Move steadily toward a concise summary and homework set.
- When you are ready to summarize (around the final turn), set progress to 100 and include a concise conclusion + homework suggestions in your reply.

Output rules (json mode):
- Return exactly one json object. No extra prose.
- The json object must include:
  - "message": string                         # Yorizo's reply to show on screen
  - "choices": object[] | []                  # Each choice: { "id": string, "label": string }
  - "suggested_next_questions": []            # Optional list of follow-up questions
  - "choice_options": string[]                # Optional short options to show as chips (e.g., ["今日から", "2〜3日前から"])
  - "progress": integer                       # 0-100: rough progress in the diagnosis flow (push to 100 when wrapping up)
  - "homework_suggestions": object[]          # Optional homework tasks; each { "title": str, "detail": str, "category": str }

Persona reminders:
- 伴走者として寄り添いながら、質問を重ねて状況を整理する。
- 必要に応じて 1〜3 件の宿題 (homework_suggestions) を提案する。小さく具体的なタスクにする。
- 選択式で答えてほしいときは choice_options を埋める。
- 10〜15問で終えられるように問いを設計し、終盤ではまとめと宿題を提示して完了へ進める。

Return valid JSON only (pay attention to quotes and commas).
""".strip()


SYSTEM_PROMPT_SMALL_BIZ = """
You are "Yorizo", a Japanese small-business advisor AI. Speak kindly and help organize concerns about sales, profit, cashflow, staffing, IT/DX, and succession, offering 3-5 concrete next steps or viewpoints.
""".strip()


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

@lru_cache()
def get_client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=settings.openai_api_key)


async def generate_chat_reply(
    messages: List[Dict[str, str]],
    with_system_prompt: bool = True,
) -> str:
    """
    Generic chat completion helper used by the RAG endpoint.

    :param messages: List of {"role": "user" | "assistant" | "system", "content": "..."}.
    :param with_system_prompt: If True, prepend SYSTEM_PROMPT_SMALL_BIZ.
    :return: The assistant's reply text (stripped).
    """
    client = get_client()

    if with_system_prompt:
        all_messages = [{"role": "system", "content": SYSTEM_PROMPT_SMALL_BIZ}] + messages
    else:
        all_messages = messages

    resp = client.chat.completions.create(
        model=settings.openai_model_chat,
        messages=all_messages,
        temperature=0.4,
    )

    content = resp.choices[0].message.content or ""
    return content.strip()


async def embed_texts(texts: Union[str, List[str]]) -> List[List[float]]:
    """
    Create vector embeddings for a single text or a list of texts using the OpenAI embeddings API.
    """
    if isinstance(texts, str):
        input_texts = [texts]
    else:
        input_texts = list(texts)

    if not input_texts:
        return []

    client = get_client()
    model_name = getattr(settings, "openai_model_embedding", DEFAULT_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL

    resp = client.embeddings.create(
        model=model_name,
        input=input_texts,
    )

    return [item.embedding for item in resp.data]


async def generate_guided_reply(
    messages: List[Dict[str, str]],
    context: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> Dict[str, object]:
    client = get_client()
    prompt_messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT_GUIDED}]
    if system_prompt:
        prompt_messages.append({"role": "system", "content": system_prompt})
    if context:
        prompt_messages.append({"role": "system", "content": f"Reference info:\n{context}"})
    prompt_messages.extend(messages[-10:])

    try:
        resp = client.chat.completions.create(
            model=settings.openai_model_chat,
            messages=prompt_messages,
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        if "message" not in data or "choices" not in data:
            raise ValueError("Model response missing required keys")
        # Normalize optional fields
        data["choices"] = data.get("choices") or []
        data["suggested_next_questions"] = data.get("suggested_next_questions") or []
        data["choice_options"] = data.get("choice_options") or []
        data["homework_suggestions"] = data.get("homework_suggestions") or []
        return data
    except OpenAIError as exc:
        logger.exception("OpenAI error during guided reply")
        raise HTTPException(status_code=502, detail="upstream AI error") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during guided reply")
        raise HTTPException(status_code=500, detail="chat generation failed") from exc


async def generate_consultation_memo(
    messages: List[Dict[str, str]],
    company_profile: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str]]:
    """
    Summarize a conversation into consultation memo bullets.

    Returns (current_concerns, important_points_for_expert).
    """
    client = get_client()
    profile_lines = []
    if company_profile:
        profile_lines = [f"{k}: {v}" for k, v in company_profile.items() if v]

    system_prompt = (
        "あなたは日本の中小企業診断士です。過去の相談内容から以下の4つを日本語で整理してください。"
        "1) current_concerns: 今回気になっていること（3〜5個の短い箇条書き）"
        "2) important_points_for_expert: 専門家に伝えたい大事なポイント（3〜5個の短い箇条書き）"
        "3) homework: 事前にやっておくとよい宿題（2〜3個の短い箇条書き）"
        "4) next_consultation_theme: 次回相談で話したいテーマ（1文）"
        "JSONのみで出力してください。"
    )

    prompt_messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if profile_lines:
        prompt_messages.append({"role": "system", "content": "会社プロフィール:\n" + "\n".join(profile_lines)})
    prompt_messages.extend(messages[-30:])

    try:
        resp = client.chat.completions.create(
            model=settings.openai_model_chat,
            messages=prompt_messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        current = data.get("current_concerns") or []
        important = data.get("important_points_for_expert") or []
        if not isinstance(current, list):
            current = [str(current)]
        if not isinstance(important, list):
            important = [str(important)]
        return [str(x) for x in current][:5], [str(x) for x in important][:5]
    except OpenAIError as exc:
        logger.exception("OpenAI error during consultation memo generation")
        raise HTTPException(status_code=502, detail="upstream AI error") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during consultation memo generation")
        user_texts = [m.get("content", "") for m in messages if m.get("role") == "user"]
        flattened = " ".join(user_texts).replace("\n", " ")
        segments = [seg.strip() for seg in flattened.split("。") if seg.strip()]
        if not segments:
            segments = ["現状の課題を教えてください。", "次に取り組みたいことを教えてください。"]
        mid = max(1, len(segments) // 2)
        return segments[:mid][:5], segments[mid:][:5]
