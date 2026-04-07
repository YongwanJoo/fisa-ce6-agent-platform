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
    "troubleshoot": ["k8s_docs", "argocd_docs", "terraform_docs"],
}

# 장애 명칭 별명 매핑 (AI 검색 품질 보강)
ALIAS_MAP = {
    "PodCrashLoopBackOff": "KubePodCrashLooping PodCrashLoopBackOff",
    "KubePodCrashLooping": "PodCrashLoopBackOff KubePodCrashLooping",
    "CPUThrottlingHigh": "KubeCPUThrottlingHigh CPUThrottlingHigh",
}

_client = QdrantClient(url=QDRANT_URL)
# n8n 자동 적재 모델과 반드시 일치해야 함 (text-embedding-3-small)
_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


def retrieve(query: str, intent: str, k: int = 5) -> list:
    # 쿼리 확장 로직 적용
    expanded_query = query
    for key, alias in ALIAS_MAP.items():
        if key in query:
            expanded_query = f"{query} {alias}"
            break

    collections = COLLECTION_MAP.get(intent, ["k8s_docs"])
    all_docs = []
    for col in collections:
        try:
            store = QdrantVectorStore(
                client=_client,
                collection_name=col,
                embedding=_embeddings,
            )
            # 확장된 쿼리로 AI 의미 검색 수행
            docs = store.similarity_search_with_score(expanded_query, k=k)
            for doc, score in docs:
                doc.metadata["score"] = score
                doc.metadata["collection"] = col
                all_docs.append(doc)
        except Exception:
            # 컬렉션이 없으면 스킵
            pass
    
    # 점수 순으로 정렬하여 상위 k개 반환
    all_docs.sort(key=lambda x: x.metadata.get("score", 0), reverse=True)
    return all_docs[:k]
