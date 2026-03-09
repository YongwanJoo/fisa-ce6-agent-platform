<img width="1024" height="338" alt="image" src="https://github.com/user-attachments/assets/87b5c235-6c99-494a-8f99-d0e7f0641a76" />

# 🤖 우리 FISA 클라우드 엔지니어링 6기 기술 세미나

> AI 에이전트 개발자를 위한 셀프서비스 배포·운영·개선 플랫폼

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
│                                          │           │
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

| 역할 | 기술 |
|------|------|
| 데이터 파이프라인 | [n8n](https://n8n.io/) |
| 벡터 DB | [Qdrant](https://qdrant.tech/) |
| 에이전트 프레임워크 | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| CI / Eval | [GitHub Actions](https://github.com/features/actions) |
| GitOps 배포 | [ArgoCD](https://argo-cd.readthedocs.io/) |
| 컨테이너 오케스트레이션 | Kubernetes (Azure AKS) |
| 관측 / 모니터링 | [Langfuse](https://langfuse.com/) |
| 클라우드 | Microsoft Azure |

---

## 🚀 로컬 실행 (준비 중)

```bash
# 1. Qdrant 실행
docker run -p 6333:6333 qdrant/qdrant

# 2. n8n 실행
docker run -p 5678:5678 n8nio/n8n

# 3. 에이전트 실행
pip install -r requirements.txt
python main.py
```

---

## 📌 참고
- [당근마켓 Kontrol — 사내 개발자 플랫폼](https://disquiet.io/@cloudtype/makerlog/당근마켓의-클라우드-관리-방식)
- [Platform Engineering이란?](https://platformengineering.org/blog/what-is-platform-engineering)
