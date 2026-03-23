# agent/

에이전트 핵심 코드가 위치하는 디렉토리입니다.

---

## 파일 설명

| 파일 | 역할 |
|------|------|
| `graph.py` | LangGraph 에이전트 그래프 정의 (전체 흐름 제어) |
| `retriever.py` | Qdrant 벡터 검색 (의도에 따라 컬렉션 선택) |
| `llm.py` | LLM 호출 — 의도 분류 / 쿼리 재작성 / 답변 생성 |
| `api.py` | FastAPI 서버 (`/query`, `/health` 엔드포인트) |
| `__init__.py` | 패키지 초기화 |

---

## 에이전트 흐름

```
사용자 입력 (에러 로그 / 정책 질문)
    ↓
[graph.py] 의도 분류
    └── "트러블슈팅" → k8s_docs + argocd_docs + resolved_cases 검색
        ↓
    [retriever.py] Qdrant 검색
        ↓
    신뢰도 평가 (score >= 0.75?)
        ├── 충분 → [llm.py] 답변 생성
        └── 부족 → 쿼리 재작성 후 재검색 (최대 3회)
                └── 여전히 부족 → "더 구체적인 로그 요청"
```

---

## API 서버 실행

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

## 가상환경 설정 (최초 1회)

```bash
# 프로젝트 루트에서
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Qdrant 컬렉션 구조

| 컬렉션명 | 용도 |
|----------|------|
| `k8s_docs` | Kubernetes 공식 문서 |
| `argocd_docs` | ArgoCD 공식 문서 |
| `resolved_cases` | 과거 해결 사례 |

> 컬렉션이 없어도 에이전트는 실행됩니다. 해당 컬렉션 검색만 스킵됩니다.
