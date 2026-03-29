# observability/

에이전트 관측(Observability) 및 자동 품질 평가(Eval) 코드가 위치하는 디렉토리입니다.

---

## 파일 설명

| 파일 | 역할 |
|------|------|
| `langfuse_setup.py` | Langfuse 트레이싱 핸들러 초기화 |
| `eval.py` | 자동 품질 평가 스크립트 (GitHub Actions에서 실행) |

---

## Langfuse란?

AI 에이전트를 위한 **관측 플랫폼**
 - 에이전트가 매 요청마다 어떤 LLM을 호출했는지, 비용·레이턴시·품질을 실시간으로 기록

### 무료로 사용하려면

1. [cloud.langfuse.com](https://cloud.langfuse.com) 에서 계정 생성
2. 프로젝트 생성 후 API 키 발급
3. `.env`에 입력:

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 자동 Eval 스크립트 (`eval.py`)

GitHub Actions CI가 코드 변경 시 자동으로 실행합니다.
**평균 점수가 0.75 미만이면 배포가 차단됩니다.**

### 로컬에서 직접 실행해보기

> `.venv`는 로컬 개발 전용입니다. CI(GitHub Actions)에서는 사용하지 않습니다.

```bash
# 가상환경 활성화 (로컬 전용)
source .venv/bin/activate

# Eval 실행
python -m observability.eval
```

### CI(GitHub Actions)에서의 실행 방식

GitHub Actions는 `.venv` 없이 시스템 Python에 직접 의존성을 설치합니다.
배포할 때마다 아래 순서로 자동 실행됩니다:

```yaml
# .github/workflows/ci.yml 내부 동작
- pip install -r requirements.txt   # 시스템 Python에 직접 설치
- python -m observability.eval      # Eval 실행 → 실패 시 배포 차단
```

### 출력 예시

```
[PASS] score=0.80 | ArgoCD sync failed: ComparisonError 오류가...
[PASS] score=1.00 | Pod가 CrashLoopBackOff 상태입니다. 원인이...
[FAIL] score=0.33 | Istio 설정이 현재 보안 정책에 위배되지 않나...

총 평균 점수: 0.71 (기준: 0.75)
❌ Eval 실패 — 배포가 차단됩니다.
```

### 테스트 케이스 추가하기

`eval.py`의 `TEST_CASES` 리스트에 추가:

```python
{
    "question": "ArgoCD OutOfSync 상태를 해결하려면?",
    "expected_keywords": ["sync", "git", "manifest", "apply"],
},
```

---

## Langfuse 대시보드에서 볼 수 있는 것들

| 항목 | 설명 |
|------|------|
| Traces | 각 요청의 전체 LLM 호출 흐름 |
| Cost | 요청당 OpenAI 비용 |
| Latency | 응답 시간 |
| Scores | Eval 점수 |
