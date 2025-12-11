from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from database import SessionLocal
from app.models import RAGDocument
from app.core.config import settings
from app.core.openai_client import embed_texts

logger = logging.getLogger(__name__)


class EmbeddingUnavailableError(RuntimeError):
    """Raised when embeddings cannot be generated (e.g., missing API key)."""


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute cosine similarity; if lengths differ, truncate to the shorter."""
    if not a or not b:
        return 0.0

    if len(a) != len(b):
        n = min(len(a), len(b))
        a = a[:n]
        b = b[:n]

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))

    if na == 0.0 or nb == 0.0:
        return 0.0

    return dot / (na * nb)


def get_store(collection_name: str) -> Dict[str, Any]:
    """
    Placeholder for collection-scoped store access.
    Current implementation is DB-backed; collection_name is carried in metadata.
    """
    return {"name": collection_name, "persist_dir": getattr(settings, "rag_persist_dir", None)}


def get_collection_name(company_id: Optional[str]) -> str:
    """company_id の有無に応じてコレクション名を一元的に決める。"""
    return f"company-{company_id}" if company_id else "global"


async def add_documents(collection_name: str, texts: List[str], metadatas: List[Dict[str, Any]]) -> List[RAGDocument]:
    """
    Embed and store documents for a given collection.
    Each metadata dict can include user_id, company_id, source_id, etc.
    """
    if not texts:
        return []

    try:
        embeddings = await embed_texts(texts)
    except RuntimeError as exc:
        logger.error("Failed to embed texts (possibly missing OpenAI API key): %s", exc)
        raise EmbeddingUnavailableError(str(exc)) from exc
    logger.info(
        "rag_add_documents",
        extra={
            "collection": collection_name,
            "count": len(texts),
            "first_meta": metadatas[0] if metadatas else None,
        },
    )
    session: Session = SessionLocal()
    saved: List[RAGDocument] = []
    try:
        for text_value, emb, meta in zip(texts, embeddings, metadatas):
            source_id = meta.get("source_id")
            user_id = meta.get("user_id")
            collection = collection_name

            doc = None
            if source_id and user_id:
                doc = (
                    session.query(RAGDocument)
                    .filter(RAGDocument.source_id == source_id, RAGDocument.user_id == user_id)
                    .first()
                )
            if doc is None:
                doc = RAGDocument()
                session.add(doc)

            doc.user_id = user_id or meta.get("company_id") or meta.get("owner_id")
            doc.title = meta.get("title") or text_value[:80]
            doc.source_type = meta.get("source_type") or "document"
            doc.source_id = source_id
            merged_meta = dict(meta or {})
            merged_meta["collection"] = collection
            doc.metadata_json = merged_meta
            doc.content = text_value
            doc.embedding = emb
            saved.append(doc)

        session.commit()
        for d in saved:
            session.refresh(d)
        logger.info(
            "rag_documents inserted",
            extra={
                "count": len(saved),
                "collection": collection_name,
                "user_ids": list({d.user_id for d in saved}),
                "doc_ids": [d.metadata_json.get("document_id") for d in saved if d.metadata_json],
            },
        )
        return saved
    finally:
        session.close()


async def similarity_search(
    collection_name: str,
    query: str,
    k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve top-k documents by cosine similarity within a collection.
    """
    try:
        query_emb_list = await embed_texts(query)
    except RuntimeError as exc:
        logger.error("Failed to embed query (possibly missing OpenAI API key): %s", exc)
        raise EmbeddingUnavailableError(str(exc)) from exc
    if not query_emb_list:
        return []
    query_emb = query_emb_list[0]

    logger.info(
        "rag_similarity_search_start",
        extra={"collection": collection_name, "filters": filters},
    )

    session: Session = SessionLocal()
    try:
        q = session.query(RAGDocument)
        if filters and filters.get("user_id"):
            q = q.filter(RAGDocument.user_id == str(filters["user_id"]))
        docs: List[RAGDocument] = q.all()
    finally:
        session.close()

    filtered_docs: List[RAGDocument] = []
    scored: List[tuple[float, RAGDocument]] = []
    for doc in docs:
        meta = doc.metadata_json or {}
        if collection_name and meta.get("collection") != collection_name:
            continue
        if filters:
            filter_user = filters.get("user_id")
            if filter_user:
                meta_user = meta.get("user_id")
                effective_user = doc.user_id or meta_user
                # user_id がメタに無い場合は除外しない。存在する場合のみ厳密一致。
                if effective_user and str(effective_user) != str(filter_user):
                    continue
            filter_company = filters.get("company_id")
            if filter_company:
                meta_company = meta.get("company_id")
                # company_id がメタに無い場合は落とさず通す（空でドロップしない）
                if meta_company not in (None, "") and str(meta_company) != str(filter_company):
                    continue

        filtered_docs.append(doc)

        emb = doc.embedding
        if not emb:
            continue
        if isinstance(emb, dict) and "embedding" in emb:
            emb = emb["embedding"]
        if not isinstance(emb, (list, tuple)):
            continue
        score = _cosine_similarity(query_emb, emb)
        scored.append((score, doc))

    logger.info(
        "rag_similarity_search_result",
        extra={"collection": collection_name, "candidate_count": len(filtered_docs)},
    )

    if not scored:
        return []

    scored.sort(key=lambda x: x[0], reverse=True)
    results: List[Dict[str, Any]] = []
    for score, doc in scored[: max(k, 1)]:
        results.append(
            {
                "id": doc.id,
                "title": doc.title,
                "text": doc.content,
                "metadata": doc.metadata_json or {},
                "score": float(score),
            }
        )
    return results


async def fetch_recent_documents(
    limit: int = 5,
    user_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch recent documents without embeddings; used for test-mode stubs.
    """
    session: Session = SessionLocal()
    try:
        q = session.query(RAGDocument).order_by(RAGDocument.created_at.desc())
        if user_id:
            q = q.filter(RAGDocument.user_id == user_id)
        if company_id:
            q = q.filter(RAGDocument.metadata_json.contains({"company_id": company_id}))
        docs: List[RAGDocument] = q.limit(max(limit, 1)).all()
    finally:
        session.close()

    return [
        {
            "id": doc.id,
            "title": doc.title,
            "text": doc.content,
            "metadata": doc.metadata_json or {},
            "score": 0.0,
        }
        for doc in docs
    ]


# Backward-compat wrappers
async def index_documents(documents: List[Dict[str, Any]], default_user_id: Optional[str] = None) -> List[RAGDocument]:
    texts: List[str] = []
    metas: List[Dict[str, Any]] = []
    for d in documents:
        texts.append(d.get("text") or "")
        meta = d.get("metadata") or {}
        if d.get("user_id") or default_user_id:
            meta["user_id"] = d.get("user_id") or default_user_id
        if d.get("source_id"):
            meta["source_id"] = d.get("source_id")
        meta.setdefault("collection", "global")
        meta.setdefault("title", d.get("title") or "")
        metas.append(meta)
    return await add_documents("global", texts, metas)


async def query_similar(question: str, k: int = 5, user_id: Optional[str] = None, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
    collection = get_collection_name(company_id)
    filters: Dict[str, Any] = {}
    if user_id and str(user_id).strip():
        filters["user_id"] = user_id
    if company_id and str(company_id).strip():
        filters["company_id"] = company_id
    return await similarity_search(collection, question, k=k, filters=filters)
