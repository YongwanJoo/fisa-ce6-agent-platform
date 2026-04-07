# AgentOps Knowledge Base (GKE SRE 도메인 지식 저장소)

이 디렉토리는 **AgentOps: 지능형 SRE 플랫폼**의 에이전트가 장애 상황을 판단하고 분석할 때 사용하는 **'단일 진실의 근원(Single Source of Truth)'** 지식 베이스입니다.

## 📂 구성 항목

1.  **[Kubernetes Troubleshooting](k8s_troubleshooting.md)**: 파드 생명주기, 네트워크 통신, 노드 및 스토리지 장애 대응 가이드
2.  **[ArgoCD Troubleshooting](argocd_troubleshooting.md)**: GitOps 동기화 오류, 자가 치유(Self-healing), 롤백 전략 가이드
3.  **[Terraform Troubleshooting](terraform_troubleshooting.md)**: IaC 상태 관리, 구성 틀어짐(Drift), 리소스 락 해제 가이드

## 🤖 에이전트 활용 가이드
- **RAG (Retrieval-Augmented Generation)**: 에이전트는 발생한 에러 로그를 바탕으로 이 문서들을 검색하여 가장 적합한 조치 권고안을 생성합니다.
- **Metadata 활용**: 각 문서 상단의 메타데이터(Category, Version)를 통해 에이전트가 지식의 최신성을 판단합니다.
- **명령어 추출**: 문서 내 포함된 `kubectl`, `terraform` 명령어들은 에이전트가 Discord 리포트에 포함하여 발송합니다.

## ✍️ 문서 업데이트 규칙
- 새로운 장애 사례나 해결 방법이 발견될 때마다 본 저장소를 업데이트하여 에이전트의 집단 지성을 강화합니다.
- 모든 명령어는 실제 운영 환경에서 검증된 안전한 명령어 위주로 작성합니다.
