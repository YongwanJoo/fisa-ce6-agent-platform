<img width="1024" height="338" alt="image" src="https://github.com/user-attachments/assets/87b5c235-6c99-494a-8f99-d0e7f0641a76" />

# 🤖 우리 FISA 클라우드 엔지니어링 6기 기술 세미나

> AWS SAA 자격증 취득을 돕는 Agentic RAG 기반 학습 플랫폼
> FISA 클라우드 엔지니어링 6기 기술 세미나

당근마켓 Kontrol에서 영감을 받아, 복잡한 인프라를 추상화하고 AI 에이전트의 전체 생애주기를 자동화하는 플랫폼입니다.

---

## 💡 기획 배경

기존 자격증 학습의 문제:
- 방대한 PDF 자료에서 원하는 개념을 **직접 찾아야** 함
- 틀린 문제를 **수동으로 정리**해야 함
- 취약한 단원이 어디인지 **파악하기 어려움**

→ 에이전트가 개념 설명, 문제 출제, 오답 분석을 **스스로 판단해서 처리**하는 학습 플랫폼을 목표로 합니다.

---

## 🏗️ 시스템 아키텍처


<img width="512" height="970" alt="스크린샷 2026-03-09 오후 11 51 24" src="https://github.com/user-attachments/assets/db7dc6e2-e84a-4b43-8d86-c9dc3d6aedd6" />

---

## ⚙️ 핵심 레이어

### 1. 데이터 파이프라인 — `n8n`
- PDF(개념 자료) → 섹션 단위 청킹 → `aws_concepts` 컬렉션 저장
- Excel(문제/정답) → 행 단위 파싱 → `aws_questions` 컬렉션 저장
- 오답 데이터 → `wrong_answers` 컬렉션 자동 누적

### 2. 에이전트 코어 — `LangGraph + Qdrant`
- 질문 의도 파악 → 적절한 컬렉션 선택
- 검색 결과 신뢰도 평가 (임계값 0.75)
- 부족하면 쿼리 재작성 후 재검색 (최대 3회)
- 틀린 문제 자동 저장 → 취약 단원 분석 → 집중 재출제

### 3. 배포 자동화 — `ArgoCD + k8s`
- GitHub Push → GitHub Actions → ArgoCD → AKS 자동 배포
- GitOps 기반 선언적 배포 파이프라인

### 4. 품질 관측 — `GitHub Actions + Langfuse`
- 배포 전 자동 Eval (프롬프트 품질 검증)
- 비용 / 레이턴시 / 재검색 횟수 / 답변 품질 실시간 트래킹

---

## 🔄 Agentic RAG 흐름

```
사용자 질문
    ↓
의도 분류
    ├── "개념 설명" → aws_concepts 검색
    └── "문제 풀기" → aws_questions 검색
        ↓
    신뢰도 평가 (score >= 0.75?)
        ├── 충분 → 답변 생성
        └── 부족 → 쿼리 재작성 → 재검색 (max 3회)
            ↓
        오답 여부 판단
            ├── 정답 → 완료
            └── 오답 → wrong_answers 저장 → 취약 단원 업데이트
```

---

## 🛠️ 기술 스택

| 역할 | 기술 | 버전 |
|------|------|------|
| 데이터 파이프라인 | [n8n](https://n8n.io/) | latest |
| 벡터 DB | [Qdrant](https://qdrant.tech/) | v1.13.x |
| 에이전트 프레임워크 | [LangGraph](https://langchain-ai.github.io/langgraph/) | 0.2.x |
| LangChain | [LangChain](https://python.langchain.com/) | 0.3.x |
| Qdrant-LangChain 통합 | [langchain-qdrant](https://pypi.org/project/langchain-qdrant/) | 1.1.x |
| PDF 파싱 | [pymupdf](https://pymupdf.readthedocs.io/) | 1.24.x |
| Excel 파싱 | [openpyxl](https://openpyxl.readthedocs.io/) | 3.1.x |
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

## 📁 디렉토리 구조

```
fisa-ce6-agent-platform/
├── README.md
├── requirements.txt
├── .gitignore
├── data/                  ← 학습 자료 (gitignore 처리)
│   └── README.md          ← 데이터 구조 설명만 문서화
├── agent/                 ← LangGraph 에이전트
│   └── .venv/             ← 가상환경 (gitignore 처리)
├── pipeline/              ← n8n 워크플로우
├── observability/         ← Langfuse 설정
└── deployment/            ← k8s, ArgoCD yaml
```

---

## 📌 참고
- [당근마켓 Kontrol — 사내 개발자 플랫폼](https://disquiet.io/@cloudtype/makerlog/당근마켓의-클라우드-관리-방식)
- [Platform Engineering이란?](https://platformengineering.org/blog/what-is-platform-engineering)
- [Agentic RAG — LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_agentic_rag/)
