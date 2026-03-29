# data/

에이전트에게 주입(Ingestion)할 원본 문서를 관리하는 보관소입니다.

---

## ☁️ 클라우드 자동화 vs 로컬 수동 적재

이 프로젝트(AgentOps)는 완전 자동화된 데이터 파이프라인을 지향합니다!
따라서 **실제 프로덕션 데이터는 이 폴더에 직접 넣지 않고**, GCP 호스팅 K8s에 떠있는 n8n이 **공식 웹사이트 URL이나 사내 Wiki API를 직접 긁어오도록** 워크플로우를 구성하는 것이 베스트 프랙티스입니다.

다만, 웹 크롤링이 불가능한 사내 보안 PDF 파일이나, 기능 구현 전에 **로컬 테스트용**으로 문서를 밀어 넣을 때는 이 디렉토리를 사용합니다. (`.pdf` 등의 용량 큰 실제 데이터 파일들은 `.gitignore` 처리되어 Git에 올라가지 않습니다.)

---

## 디렉토리 구조 (테스트용)

```
data/
├── k8s/           ← Kubernetes 문서 테스트용 PDF
├── argocd/        ← ArgoCD 문서 테스트용 PDF
├── terraform/     ← Terraform 문서 테스트용 PDF
└── resolved/      ← 과거 해결 사례 백업 (Markdown)
```

## 🛠️ 파일 기반수동 적재 방법 

사내망 등 이유로 URL 크롤링 자동화가 아예 불가능하여 부득이하게 파일을 직접 클라우드 n8n 포드에 넘겨야 한다면 다음 방식을 사용합니다.

**1. 로컬 환경 테스트 시**
이 폴더에 PDF를 넣고 브라우저 `localhost:5678` 의 로컬 n8n에서 "Read PDF File" 노드로 읽어들입니다.

**2. GCP GKE 프로덕션 환경 시**
n8n이 GKE 클러스터 안에 떠 있으므로, 로컬 노트북에 있는 문서를 파드 안으로 복사해야 n8n이 읽을 수 있습니다.
```bash
# 로컬 data 폴더 안의 PDF를 n8n 파드의 특정 경로(마운트된 볼륨 등)로 복사 (sre-agent Ns)
kubectl cp data/k8s/docs.pdf $(kubectl get pods -n sre-agent -l app=n8n -o jsonpath='{.items[0].metadata.name}'):/tmp/docs.pdf -n sre-agent
```
이후 클라우드 n8n 워크플로우에서 경로를 `/tmp/docs.pdf`로 지정하여 읽어들입니다.

---

### 해결 사례 (Resolved Cases) 관리 팁
`resolved/` 에는 과거 트러블슈팅 사례를 마크다운으로 작성해두면 좋습니다.
(이 파일 역시 GitHub보다는 사내 Notion/Wiki에 올려두고 n8n이 API로 매일 새로고침 해오는 방식이 훨씬 AgentOps 다운 운영 방식입니다!)
