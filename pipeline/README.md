# pipeline/

GKE 내부에 배포된 n8n 자동화 파이프라인을 관리하는 디렉토리입니다.

---

## 왜 n8n을 GKE 안에 올렸나요?

로컬 노트북에서 n8n을 실행하면 노트북을 끄는 순간 크롤링이 멈춥니다. GKE 내부에 n8n을 배포하면 다음이 가능합니다.

- **지속적 자동화**: 매일 새벽 공식 문서 URL을 스캔해 Qdrant에 임베딩 적재
- **내부망 고속 통신**: 에이전트, Qdrant, n8n이 동일한 클러스터 안에서 `http://qdrant-svc:6333`으로 직접 통신

---

## 워크플로우 목록

| 파일 | 목적 | 트리거 |
|------|------|--------|
| `k8s_docs_ingest.json` | K8s·ArgoCD 공식 문서 크롤링 → `k8s_docs` 컬렉션 적재 | 매일 00:00 |
| `resolved_cases_ingest.json` | 사내 Wiki 해결 사례 크롤링 → `resolved_cases` 컬렉션 적재 | 매일 03:00 |

> 워크플로우는 n8n UI에서 완성 후 Export해 이 디렉토리에 백업합니다.

---

## n8n 접속 및 설정

**1. 포트포워딩으로 UI 열기**

```bash
kubectl port-forward svc/n8n-svc 5678:5678 -n sre-agent
```

**2. 웹 접속**

`http://localhost:5678` 으로 접속합니다. (최초 접속 시 관리자 계정 생성)

**3. 워크플로우 복원**

1. 우상단 메뉴 → **Import from File** 클릭
2. 이 디렉토리의 `.json` 파일 선택
3. Qdrant Credential 설정에 클러스터 내부 주소 입력:
   - URL: `http://qdrant-svc:6333`
4. **Activate 토글 켜기**

---

## 트러블슈팅

**워크플로우가 실행되지 않는 경우**

```bash
kubectl logs -n sre-agent deploy/n8n
```

**Qdrant Connection Error**

Qdrant URL이 `localhost`가 아닌 GKE 내부 주소로 설정되어 있는지 확인합니다.

```
올바른 주소: http://qdrant-svc:6333
잘못된 주소: http://localhost:6333  (로컬 전용)
```
