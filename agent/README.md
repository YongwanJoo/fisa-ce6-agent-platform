# agent/

FastAPI 서버와 LangGraph 에이전트 핵심 코드가 위치하는 디렉토리입니다.

---

## 파일 구조

```
agent/
├── api.py          # FastAPI 서버 (/query, /health, /webhook/alertmanager)
├── graph.py        # LangGraph 에이전트 상태 머신 (전체 흐름 제어)
├── llm.py          # LLM 호출 — 의도 분류 / 쿼리 재작성 / 답변 생성
├── retriever.py    # Qdrant 벡터 검색 (의도에 따라 컬렉션 선택)
└── __init__.py     # 패키지 초기화
```

---

## 에이전트 처리 흐름

```
사용자 입력 / AlertManager Webhook
       │
  [graph.py] 의도 분류
       │
  [retriever.py] Qdrant 검색
  ├── k8s_docs        (Kubernetes 공식 문서)
  ├── argocd_docs     (ArgoCD 공식 문서)
  └── resolved_cases  (과거 해결 사례)
       │
  신뢰도 평가 (score >= 0.75?)
  ├── 충분  → [llm.py] 답변 생성
  └── 부족  → 쿼리 재작성 후 재검색 (최대 3회)
                └── 여전히 부족 → "더 구체적인 로그 요청"
```

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/query` | 사용자 질문 수신 → 에이전트 실행 → 답변 반환 |
| `GET` | `/health` | 헬스체크 |
| `POST` | `/webhook/alertmanager` | AlertManager Webhook 수신 → 백그라운드 분석 + Discord 보고 |

### 실행

```bash
# 프로젝트 루트에서 실행
uvicorn agent.api:app --reload --port 8000
```

### 요청 예시

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Pod가 CrashLoopBackOff 상태입니다. 원인이 뭔가요?"}'
```

### 응답 예시

```json
{
  "answer": "CrashLoopBackOff는 컨테이너가 반복적으로 실패할 때 발생합니다...",
  "intent": "troubleshoot",
  "retry_count": 0
}
```

---

## Qdrant 컬렉션 구조

| 컬렉션명 | 용도 |
|----------|------|
| `k8s_docs` | Kubernetes 공식 문서 |
| `argocd_docs` | ArgoCD 공식 문서 |
| `resolved_cases` | 과거 해결 사례 |

> 컬렉션이 없어도 에이전트는 실행됩니다. 해당 컬렉션 검색만 스킵됩니다.

---

## 환경변수

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 (필수) |
| `QDRANT_URL` | Qdrant 주소 (로컬: `http://localhost:6333`, GKE: `http://qdrant-svc:6333`) |
| `DISCORD_WEBHOOK_URL` | Discord 알람 전송용 Webhook URL |
| `LANGFUSE_PUBLIC_KEY` | Langfuse 트레이싱 공개 키 |
| `LANGFUSE_SECRET_KEY` | Langfuse 트레이싱 비밀 키 |
| `LANGFUSE_HOST` | Langfuse 리전 주소 (예: `https://us.cloud.langfuse.com`) |
