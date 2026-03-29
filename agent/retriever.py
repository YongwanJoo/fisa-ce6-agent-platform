"""
Qdrant 검색 — 의도에 따라 컬렉션 선택
"""
import os
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

# 의도별 컬렉션 매핑
COLLECTION_MAP = {
    "troubleshoot": ["k8s_docs", "argocd_docs", "resolved_cases"],
}

_client = QdrantClient(url=QDRANT_URL)
_embeddings = OpenAIEmbeddings()


def retrieve(query: str, intent: str, k: int = 5) -> list:
    collections = COLLECTION_MAP.get(intent, ["k8s_docs"])
    all_docs = []
    for col in collections:
        try:
            store = QdrantVectorStore(
                client=_client,
                collection_name=col,
                embedding=_embeddings,
            )
            docs = store.similarity_search_with_score(query, k=k)
            for doc, score in docs:
                doc.metadata["score"] = score
                doc.metadata["collection"] = col
            all_docs.extend([doc for doc, _ in docs])
        except Exception:
            # 컬렉션이 없으면 스킵
            pass
    return all_docs
