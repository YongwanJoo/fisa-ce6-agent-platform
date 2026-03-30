# data/

에이전트에게 주입할 원본 지식 문서를 관리하는 디렉토리입니다.

---

## 파일 구조

```
data/
├── k8s_troubleshooting.md       # Kubernetes 트러블슈팅 문서
├── argocd_troubleshooting.md    # ArgoCD 트러블슈팅 문서
└── terraform_troubleshooting.md # Terraform 트러블슈팅 문서
```

> PDF 등 용량 큰 실제 데이터 파일은 `.gitignore` 처리되어 Git에 올라가지 않습니다.

---

## 데이터 적재 방식

이 프로젝트는 **n8n이 공식 문서 URL을 직접 크롤링**하는 완전 자동화 방식을 기본으로 합니다. 이 디렉토리는 크롤링이 불가능한 사내 문서나 로컬 테스트 시에만 사용합니다.

| 상황 | 방식 |
|------|------|
| **프로덕션 (GKE)** | n8n이 공식 URL을 자동 크롤링 → Qdrant 적재 (매일 자동) |
| **로컬 테스트** | 이 디렉토리에 파일 추가 → `test_data.py`로 수동 적재 |
| **사내 보안 문서** | 아래 `kubectl cp` 방식으로 n8n 파드에 직접 복사 |

---

## 로컬 테스트 시 수동 적재

```bash
# 1. 로컬 Qdrant 실행 중인지 확인
#    http://localhost:6333/dashboard

# 2. 시딩 스크립트 실행
export QDRANT_URL=http://localhost:6333
python test_data.py
```

---

## GKE 환경에서 사내 문서 적재

웹 크롤링이 불가능한 사내 문서를 GKE n8n 파드에 직접 복사하는 방법입니다.

```bash
# 로컬 파일을 n8n 파드 내부로 복사
kubectl cp data/k8s_troubleshooting.md \
  $(kubectl get pods -n sre-agent -l app=n8n -o jsonpath='{.items[0].metadata.name}'):/tmp/docs.md \
  -n sre-agent
```

이후 n8n 워크플로우에서 경로를 `/tmp/docs.md`로 지정해 읽어들입니다.

---

## 해결 사례 관리 팁

과거 트러블슈팅 사례는 마크다운 형식으로 정리해 이 디렉토리에 저장하거나, 사내 Notion/Wiki에 올려두고 n8n이 API로 매일 새로고침하는 방식을 권장합니다.

```markdown
# [에러명] 해결 사례

## 현상
...

## 원인
...

## 해결
...
```
