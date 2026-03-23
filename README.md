<img width="1024" height="338" alt="image" src="https://github.com/user-attachments/assets/87b5c235-6c99-494a-8f99-d0e7f0641a76" />

# 🤖 우리 FISA 클라우드 엔지니어링 6기 기술 세미나

> **AgentOps** — AI 에이전트를 GitOps 기반 완전 관리형 인프라에 배포/운영하는 플랫폼
> (GCP K8s + n8n 완전 클라우드 자동화 구조 적용)

ArgoCD / Kubernetes 운영 중 발생하는 에러 로그를 분석하고, 공식 문서·과거 사례를 기반으로 해결책을 제시하는 **SRE 에이전트**입니다.

이 시스템의 핵심은 단순한 RAG 봇이 아니라, **에이전트를 어떻게 배포하고, 데이터를 어떻게 최신화하며(n8n 클라우드 내부망 통신), 퀄리티를 평가(Eval)하는지 보여주는 "AgentOps"의 완성형 무선망 파이프라인**을 띄우는 것에 있습니다.

---

## 📌 전체 아키텍처 (GCP GKE + 자동화 인프라)

```
[인터넷 / 사내망 오픈]                    [GCP GKE 클러스터 내부 (sre-agent Ns)]
 LoadBalancer (80)     →        API 에이전트 (Pod)
                           (인터넷 차단 내부통신 ↓ API 호출: http://qdrant-svc:6333)
                              Qdrant DB (Pod) ←동적 마운트→ [GCP 영구 디스크 5GB]
                           (인터넷 차단 내부통신 ↑ 문서 적재: http://qdrant-svc:6333)
 Port-Forward (5678)   →        n8n 파이프라인 (Pod) ←동적 마운트→ [GCP 영구 디스크 5GB]
```

**✅ 왜 GCP 클라우드 내부에 에이전트 + Qdrant + n8n을 한 번에 배포했나요?**
1. **완벽한 데이터 자동화**: 노트북을 꺼도 새벽마다 클라우드 안(n8n Pod)에서 `kubernetes.io` 공식 문서를 자동으로 크롤링/임베딩해 옆 파드(Qdrant)에 꽂아 넣습니다.
2. **비용 효율 및 안정성**: 영구 볼륨(Persistent Disk)을 엮어 노드가 재부팅되어도 벡터 데이터가 1원도 유실되지 않습니다.

---

## 🛠️ 필요한 가이드

이 프로젝트는 **로컬 테스트**와 **완벽한 GCP 배포** 모두 가능합니다. 

- **빠르게 클라우드에 전체 인프라를 띄우고 싶다면**: 👉 [GCP GKE 배포 전체 라인 상세 가이드](deployment/README.md)
- **n8n 자동 파이프라인 구성이 궁금하다면**: 👉 [클라우드 백업 자동화 (n8n) 가이드](pipeline/README.md)
- **로컬에서 파이썬 에이전트 코드만 띄워보고 싶다면**: 아래 로컬 실행을 따라주세요.

---

## 🚀 로컬 개발환경 실행 가이드

> 배포가 아닌 순수 에이전트 봇 자체를 로컬에서 돌려보는 단계입니다.

### Step 1. 레포 클론 및 환경 설정

```bash
git clone https://github.com/nyongwan/fisa-ce6-agent-platform.git
cd fisa-ce6-agent-platform

# .env.example을 복사해서 .env 파일 생성
cp .env.example .env

# 파이썬 가상환경
python3 -m venv .venv
source .venv/bin/activate 

pip install -r requirements.txt
```

`.env` 파일을 열어서 필수 값 1개를 꼭 채웁니다:
```env
OPENAI_API_KEY=sk-...         # 필수: OpenAI API 키
QDRANT_URL=http://localhost:6333  # 로컬용 유지
```

### Step 2. 로컬용 Qdrant 실행 (컨테이너)
데이터베이스 역할을 할 벡터 DB입니다.
```bash
# Docker 또는 Podman
podman run -d --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/qdrant_data:/qdrant/storage:Z \
  docker.io/qdrant/qdrant:v1.13.0
```
✅ 확인: http://localhost:6333/dashboard 접속되면 성공

### Step 3. 에이전트 로컬 실행

```bash
# 옵션 1: CLI 모드 (터미널에서 직접 물어보기)
python main.py

# 옵션 2: API 챗봇 서버 모드 
uvicorn agent.api:app --reload --port 8000
```

---

## 🔄 AgentOps 파이프라인 CI/CD 흐름

```
개발자의 Agent 프롬프트 / 코드 변경
    ↓
GitHub Push
    ↓
GitHub Actions
    ├── [Eval] 테스트 스크립트 실행 (품질 통과?)
    │       ├── 통과(Pass) → 이미지 빌드 후 GHCR 등재 
    │       └── 실패(Fail점수) → 즉시 배포 중단 ❌
    ↓
ArgoCD가 깃 변경 감지 → GKE 클러스터에 Sync
    ↓
Langfuse로 배포 이후 실시간 관측
    (비용 / 레이턴시 / 답변 품질 실시간 추적)
```

---

## 🛠️ 기술 스택

| 역할 | 기술 | 버전 |
|------|------|------|
| 클라우드 인프라 | **Google Cloud Platform (GKE)** | Standard / Autopilot |
| GitOps 배포 | [ArgoCD](https://argo-cd.readthedocs.io/) | latest |
| 데이터 파이프라인 | [n8n](https://n8n.io/) | latest |
| 에이전트 프레임워크 | [LangGraph](https://langchain-ai.github.io/langgraph/) | 0.2.x |
| 벡터 DB | [Qdrant](https://qdrant.tech/) | v1.13.x |
| 에이전트 관측 | [Langfuse](https://langfuse.com/) | 2.x |
| LLM | [OpenAI GPT-4o-mini](https://openai.com) | - |

---

## 📌 참고 자료

- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [LangGraph Agentic RAG 튜토리얼](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_agentic_rag/)
