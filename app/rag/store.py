from typing import List, Dict

from fastapi import HTTPException

from app.core.config import settings
from app.core.openai_client import embed_texts

CHROMA_AVAILABLE = False
chromadb = None
ChromaSettings = None
_client = None
_collection = None

try:
    if settings.rag_enabled:
        import chromadb as _chromadb
        from chromadb.config import Settings as _ChromaSettings

        chromadb = _chromadb
        ChromaSettings = _ChromaSettings
        CHROMA_AVAILABLE = True
    else:
        CHROMA_AVAILABLE = False
except Exception:
    CHROMA_AVAILABLE = False
    chromadb = None
    ChromaSettings = None

if CHROMA_AVAILABLE:
    try:
        _client = chromadb.PersistentClient(
            path=settings.rag_persist_dir,
            settings=ChromaSettings(allow_reset=True),
        )
        _collection = _client.get_or_create_collection(name="yorizo-kb")
    except Exception:
        CHROMA_AVAILABLE = False
        _client = None
        _collection = None


def _ensure_chroma() -> None:
    if not CHROMA_AVAILABLE or chromadb is None or ChromaSettings is None or _client is None or _collection is None:
        raise HTTPException(
            status_code=503,
            detail="RAG (document search) is temporarily disabled in this environment.",
        )


async def index_documents(docs: List[Dict]) -> None:
    """
    docs: [{ "id": str, "text": str, "metadata": dict }, ...]
    """
    _ensure_chroma()
    if not docs:
        return

    texts = [d["text"] for d in docs]
    ids = [d["id"] for d in docs]
    metadatas = [d.get("metadata", {}) for d in docs]

    embeddings = await embed_texts(texts)

    _collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )


async def query_similar(query: str, k: int = 5) -> List[Dict]:
    """
    Return top-k similar documents with text + metadata.
    """
    _ensure_chroma()
    query_embedding = (await embed_texts([query]))[0]

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
    )

    docs: List[Dict] = []
    for i in range(len(results["ids"][0])):
        docs.append(
            {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if "distances" in results else None,
            }
        )
    return docs
