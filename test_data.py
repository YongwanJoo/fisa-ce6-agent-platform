import os
from dotenv import load_dotenv

load_dotenv()

from agent.retriever import _client, _embeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore

def main():
    print("🌱 테스트용 더미 데이터(K8s/ArgoCD 문서)를 Qdrant에 적재합니다...")
    url = os.getenv("QDRANT_URL", "http://localhost:6333")

    dummy_docs = {
        "k8s_docs": [
            Document(
                page_content="Pod가 CrashLoopBackOff 상태에 빠지는 주된 원인은 컨테이너 내부 애플리케이션 시작 실패, 메모리 부족(OOMKilled), 혹은 잘못된 시작 명령(command/args)입니다. 해결하려면 가장 먼저 `kubectl logs <pod-name>` 명령어로 컨테이너 로그를 확인하고, `kubectl describe pod <pod-name>`으로 최근 이벤트를 점검해야 합니다.",
                metadata={"source": "kubernetes-docs", "section": "troubleshooting"}
            ),
        ],
        "argocd_docs": [
            Document(
                page_content="ArgoCD에서 앱이 OutOfSync 상태가 되는 것은 Git 저장소(Desired State)의 매니페스트와 K8s 클러스터(Live State)의 상태가 달라졌기 때문입니다. 자동 Sync가 꺼져 있거나 적용이 실패했을 수 있습니다. 해결하려면 Sync 버튼을 누르거나 ComparisonError 상세 메시지를 확인하세요.",
                metadata={"source": "argocd-docs", "section": "sync-status"}
            ),
        ],
        "resolved_cases": [
            Document(
                page_content="[사내 장애 사례 해결] Pod CrashLoopBackOff 지속 발생 건: 애플리케이션 코드 이상은 없었으나, DB 접속 정보를 가지고 있는 Secret 환경변수 명이 틀려서 (DB_HOST -> DATABASE_HOST) 앱이 구동되자마자 즉시 뻗어버리는 문제였습니다. yaml 파일 내 env 설정을 교정하여 해결했습니다.",
                metadata={"source": "wiki-resolved-cases", "author": "sre-team"}
            ),
        ]
    }

    for collection_name, docs in dummy_docs.items():
        try:
            # 컬렉션 존재 여부 확인 (없으면 에러 발생)
            _client.get_collection(collection_name)
            print(f"✅ '{collection_name}' 컬렉션이 이미 존재합니다.")
        except Exception:
            print(f"🚀 '{collection_name}' 컬렉션 생성 및 샘플 벡터 임베딩 중...")
            QdrantVectorStore.from_documents(
                docs,
                _embeddings,
                url=url,
                collection_name=collection_name,
            )
            
    print("\n🎉 모든 데이터 시딩 완료! 이제 에이전트가 답변할 수 있습니다.")

if __name__ == "__main__":
    main()
