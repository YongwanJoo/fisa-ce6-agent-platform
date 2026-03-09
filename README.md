<img width="1024" height="338" alt="image" src="https://github.com/user-attachments/assets/87b5c235-6c99-494a-8f99-d0e7f0641a76" />

# 🤖 fisa-ce6-agent-platform

> AI 에이전트 개발자를 위한 셀프서비스 배포·운영·개선 플랫폼
> FISA 클라우드 엔지니어링 6기 기술 세미나

당근마켓 Kontrol에서 영감을 받아, 복잡한 인프라를 추상화하고 AI 에이전트의 전체 생애주기를 자동화하는 플랫폼입니다.

---

## 💡 기획 배경

기존 AI 에이전트 개발의 문제:
- 에이전트 코드를 짜는 것보다 **배포/운영 환경 세팅에 더 많은 시간**이 소요됨
- 에이전트 품질 검증, 모니터링을 **수동**으로 처리
- 데이터 업데이트, 재배포를 **사람이 직접** 트리거

→ 에이전트 개발자가 **인프라를 몰라도** 배포·운영·개선할 수 있는 플랫폼을 목표로 합니다.

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                  AgentOps Platform                  │
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌───────────────┐  │
│  │   n8n    │───▶│  Qdrant  │───▶│   LangGraph   │  │
│  │ Pipeline │    │ VectorDB │    │    Agent      │  │
│  └──────────┘    └──────────┘    └───────┬───────┘  │
│                                          │          │
│  ┌──────────┐    ┌──────────┐    ┌───────▼───────┐  │
│  │  ArgoCD  │◀───│  GitHub  │    │   Langfuse    │  │
│  │  GitOps  │    │ Actions  │    │  Observability│  │
│  └──────────┘    └──────────┘    └───────────────┘  │
│                                                     │
│                 Azure AKS (k8s)                     │
└─────────────────────────────────────────────────────┘
```

---

## ⚙️ 핵심 레이어

### 1. 데이터 파이프라인 — `n8n`
- 금융 뉴스 스케줄 자동 수집
- 텍스트 벡터화(Embedding) 후 Qdrant 저장
- 에이전트 지식 창고 자동 업데이트

### 2. 에이전트 코어 — `LangGraph + Qdrant`
- LangGraph 기반 에이전트 로직 구성
- Qdrant RAG(Retrieval-Augmented Generation) 연동

### 3. 배포 자동화 — `ArgoCD + k8s`
- GitHub Push → GitHub Actions → ArgoCD → AKS 자동 배포
- GitOps 기반 선언적 배포 파이프라인

### 4. 품질 관측 — `GitHub Actions + Langfuse`
- 배포 전 자동 Eval(프롬프트 품질 검증)
- 비용 / 레이턴시 / 답변 품질 실시간 트래킹

---

## 🛠️ 기술 스택

| 역할 | 기술 | 버전 |
|------|------|------|
| 데이터 파이프라인 | [n8n](https://n8n.io/) | latest |
| 벡터 DB | [Qdrant](https://qdrant.tech/) | v1.13.x |
| 에이전트 프레임워크 | [LangGraph](https://langchain-ai.github.io/langgraph/) | 0.2.x |
| LangChain | [LangChain](https://python.langchain.com/) | 0.3.x |
| Qdrant-LangChain 통합 | [langchain-qdrant](https://pypi.org/project/langchain-qdrant/) | 1.1.x |
| API 서버 | [FastAPI](https://fastapi.tiangolo.com/) | 0.115.x |
| CI / Eval | [GitHub Actions](https://github.com/features/actions) | - |
| GitOps 배포 | [ArgoCD](https://argo-cd.readthedocs.io/) | latest |
| 컨테이너 오케스트레이션 | Kubernetes (Azure AKS) | - |
| 관측 / 모니터링 | [Langfuse](https://langfuse.com/) | 2.x |
| 클라우드 | Microsoft Azure | - |
| 런타임 | Python | 3.11+ |

> ⚠️ **버전 호환성 주의**: Qdrant 서버와 `qdrant-client`의 메이저 버전은 반드시 일치해야 하며, 마이너 버전 차이는 1 이하여야 합니다.

---

## 🚀 로컬 실행

```bash
# 1. Qdrant 실행 (버전 고정 권장)
docker run -d --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/qdrant_data:/qdrant/storage \
  qdrant/qdrant:v1.13.0

# 2. n8n 실행
docker run -d --name n8n \
  -p 5678:5678 \
  n8nio/n8n:latest

# 3. 의존성 설치 (Python 3.11+ 권장)
pip install -r requirements.txt

# 4. 에이전트 실행
python main.py
```

> 💡 Qdrant 대시보드: http://localhost:6333/dashboard
> 💡 n8n 대시보드: http://localhost:5678

---

## 📌 참고
- [당근마켓 Kontrol — 사내 개발자 플랫폼](https://disquiet.io/@cloudtype/makerlog/당근마켓의-클라우드-관리-방식)
- [Platform Engineering이란?](https://platformengineering.org/blog/what-is-platform-engineering)
