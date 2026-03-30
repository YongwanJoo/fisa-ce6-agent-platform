# observability/

에이전트 관측(Observability) 및 자동 품질 평가(Eval) 코드가 위치하는 디렉토리입니다.

---

## 파일 구조

```
observability/
├── eval.py             # CI 자동 품질 평가 스크립트 (점수 미달 시 배포 차단)
├── langfuse_setup.py   # Langfuse 트레이싱 핸들러 초기화
└── golden_set.json     # 평가 기준 질문-정답 셋
```

---

## Langfuse 트레이싱

에이전트가 매 요청마다 어떤 LLM을 호출했는지, 비용·레이턴시·품질을 실시간으로 기록하는 관측 플랫폼입니다.

**설정 방법**

1. [cloud.langfuse.com](https://cloud.langfuse.com) 에서 계정 생성
2. 프로젝트 생성 후 API 키 발급
3. `.env`에 입력:

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com   # 본인 계정 리전에 맞게 설정
```

**대시보드에서 확인할 수 있는 항목**

| 항목 | 설명 |
|------|------|
| Traces | 각 요청의 전체 LLM 호출 흐름 |
| Cost | 요청당 OpenAI 비용 |
| Latency | 응답 시간 |
| Scores | Eval 점수 |

---

## 자동 Eval (eval.py)

GitHub Actions CI가 코드 변경 시 자동으로 실행됩니다. **평균 점수가 0.75 미만이면 배포가 차단됩니다.**

### 로컬 실행

```bash
source .venv/bin/activate
python -m observability.eval
```

### 출력 예시

```
[PASS] score=0.80 | ArgoCD sync failed: ComparisonError 오류가...
[PASS] score=1.00 | Pod가 CrashLoopBackOff 상태입니다. 원인이...
[FAIL] score=0.33 | Istio 설정이 현재 보안 정책에 위배되지 않나...

총 평균 점수: 0.71 (기준: 0.75)
❌ Eval 실패 — 배포가 차단됩니다.
```

### CI에서의 실행 방식

GitHub Actions는 `.venv` 없이 시스템 Python에 직접 의존성을 설치합니다.

```yaml
# .github/workflows/ci.yml 내부 동작
- pip install -r requirements.txt
- python -m observability.eval      # 실패 시 이후 단계 전체 차단
```

### 테스트 케이스 추가

`eval.py`의 `TEST_CASES` 리스트에 추가합니다:

```python
{
    "question": "ArgoCD OutOfSync 상태를 해결하려면?",
    "expected_keywords": ["sync", "git", "manifest", "apply"],
},
```
