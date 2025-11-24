from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.openai_client import generate_chat_reply
from app.rag.store import index_documents, query_similar
from app.schemas.rag import (
    RagChatRequest,
    RagChatResponse,
    RagDocumentCreate,
    RagDocumentResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagSimilarDocument,
)
from database import get_db
from models import RAGDocument

router = APIRouter()


@router.post("/rag/documents", response_model=RagDocumentResponse)
async def create_rag_document(payload: RagDocumentCreate) -> RagDocumentResponse:
    """
    Register a single RAG document and store its embedding.
    """
    try:
        saved_docs = await index_documents([payload.model_dump()])
        if not saved_docs:
            raise HTTPException(status_code=500, detail="Failed to save document")
        return RagDocumentResponse.model_validate(saved_docs[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/rag/documents", response_model=list[RagDocumentResponse])
async def list_rag_documents(
    user_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[RagDocumentResponse]:
    query = db.query(RAGDocument).order_by(RAGDocument.created_at.desc())
    if user_id:
        query = query.filter(RAGDocument.user_id == user_id)
    docs = query.limit(limit).all()
    return [RagDocumentResponse.model_validate(doc) for doc in docs]


@router.post("/rag/search", response_model=RagQueryResponse)
async def rag_search(payload: RagQueryRequest) -> RagQueryResponse:
    """
    Return the most similar stored documents for a query.
    """
    try:
        results = await query_similar(payload.question, k=payload.top_k, user_id=payload.user_id)
        matches = [
            RagSimilarDocument(
                id=doc["id"],
                title=doc["title"],
                text=doc["text"],
                metadata=doc.get("metadata") or {},
                score=float(doc.get("score", 0.0)),
            )
            for doc in results
        ]
        return RagQueryResponse(matches=matches)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/rag/chat", response_model=RagChatResponse)
async def rag_chat_endpoint(payload: RagChatRequest) -> RagChatResponse:
    """
    RAG-style chat for Japanese small business owners.
    """
    try:
        docs = await query_similar(payload.question, k=5, user_id=payload.user_id)
        context_texts = [d["text"] for d in docs]

        system_content = (
            "あなたは日本の小規模事業者を支援する経営相談AI『Yorizo』です。"
            "以下の「参考情報」を踏まえつつ、質問に日本語で答えてください。"
            "参考情報に書かれていないことを推測で断定せず、"
            "売上・利益・資金繰り・人手不足・IT・DX・税務などの観点から、"
            "3〜5個の具体的な視点や次の一歩を提案してください。"
        )

        context_block = "\n\n".join([f"【参考情報{i+1}】\n{txt}" for i, txt in enumerate(context_texts)])

        messages = [
            {"role": "system", "content": system_content},
            {"role": "system", "content": f"参考情報:\n{context_block}" if context_block else "参考情報はありません。"},
        ]

        for history_item in payload.history:
            messages.append({"role": "user", "content": history_item})

        messages.append({"role": "user", "content": payload.question})

        answer = await generate_chat_reply(messages, with_system_prompt=False)

        return RagChatResponse(answer=answer, contexts=context_texts)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
