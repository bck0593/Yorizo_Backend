from typing import List, Dict
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
from app.core.openai_client import embed_texts

_client = chromadb.PersistentClient(
    path=settings.rag_persist_dir,
    settings=ChromaSettings(allow_reset=True),
)
_collection = _client.get_or_create_collection(name="yorizo-kb")


async def index_documents(docs: List[Dict]) -> None:
    """
    docs: [{ "id": str, "text": str, "metadata": dict }, ...]
    """
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
