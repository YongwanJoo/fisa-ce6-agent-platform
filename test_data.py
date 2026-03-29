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
            Document(
                page_content="OOMKilled 에러를 해결하는 방법: OOMKilled는 컨테이너가 지정된 메모리 제한(limit)을 초과해서 강제 종료되었음을 의미합니다. 파드의 resources.limits.memory 값을 높이거나 애플리케이션 메모리 누수(리소스 확보)를 점검하세요.",
                metadata={"source": "kubernetes-docs", "section": "troubleshooting"}
            ),
            Document(
                page_content="k8s 서비스 타입 중 LoadBalancer와 ClusterIP의 차이: ClusterIP는 클러스터 내부 전용 통신용 IP를 할당하므로 외부에서 접근할 수 없습니다. LoadBalancer는 외부 클라우드 제공자의 서비스 로드밸런서를 생성해 외부 IP를 할당하여 원격 접속 및 외부 접근이 가능하게 만듭니다.",
                metadata={"source": "kubernetes-docs", "section": "networking"}
            )
        ],
        "argocd_docs": [
            Document(
                page_content="ArgoCD에서 앱이 OutOfSync 상태가 지속될 때 조치 방법: OutOfSync 상태는 Git 저장소의 매니페스트와 클러스터 상태가 다름을 동기화 의미합니다. 수동으로 Sync 버튼을 누르거나 자동 동기화(Self-Heal) 설정을 켜서 해결할 수 있습니다.",
                metadata={"source": "argocd-docs", "section": "sync-status"}
            ),
            Document(
                page_content="ArgoCD sync failed: ComparisonError 오류는 주로 배포 매니페스트(yaml) 문법 오류, Git 지원하지 않는 리소스 버전, 혹은 이미지 태그 누락 등으로 발생합니다. 확인 방법은 kubectl describe pod 로 상세 이유 로그를 확인하는 것입니다.",
                metadata={"source": "argocd-docs", "section": "troubleshooting"}
            )
        ],
        "resolved_cases": [
            Document(
                page_content="[사내 장애 사례 해결] Pod CrashLoopBackOff 지속 발생 건: 재시작이 무한 루프 도는 현상. 애플리케이션 코드 이상은 없었으나, DB 접속 정보를 가지고 있는 Secret 환경변수 명이 틀려서 (DB_HOST -> DATABASE_HOST) 앱이 구동되자마자 즉시 뻗어버리는 문제였습니다. yaml 파일 내 env 설정을 교정하여 해결했습니다.",
                metadata={"source": "wiki-resolved-cases", "author": "sre-team"}
            ),
        ]
    }

    for collection_name, docs in dummy_docs.items():
        print(f"🚀 '{collection_name}' 컬렉션 생성(Recreate) 및 지식 임베딩 중...")
        QdrantVectorStore.from_documents(
            docs,
            _embeddings,
            url=url,
            collection_name=collection_name,
            force_recreate=True,
        )
            
    print("\n🎉 모든 데이터 시딩 완료! 이제 에이전트가 답변할 수 있습니다.")

if __name__ == "__main__":
    main()
