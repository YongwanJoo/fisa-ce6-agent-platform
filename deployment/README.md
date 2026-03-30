# deployment/

GKE 배포용 Kubernetes 매니페스트와 ArgoCD GitOps 설정 파일이 위치하는 디렉토리입니다.

---

## 파일 구조

```
deployment/
├── namespace.yaml          # K8s 네임스페이스 생성 (sre-agent)
├── deployment.yaml         # SRE 에이전트 파드 배포 설정
├── service.yaml            # 에이전트 외부 공개용 LoadBalancer 설정
├── qdrant.yaml             # Qdrant DB 파드 + GCP 영구 디스크 연결
├── n8n.yaml                # n8n 파이프라인 파드 + GCP 영구 디스크 연결
├── argocd-app.yaml         # GitOps 배포 파이프라인 구성
├── secret.example.yaml     # API 키 설정 템플릿
└── prometheus/
    ├── values.yaml         # kube-prometheus-stack Helm values
    ├── alert-rules.yaml    # PrometheusRule (CrashLoopBackOff, OOMKilled 감지)
    └── dummy-fail-pod.yaml # 알람 테스트용 의도적 실패 파드
```

---

## GCP GKE 배포 순서 (최초 1회)

> 전제: GCP 콘솔에서 GKE 클러스터가 생성되어 있고, `gcloud container clusters get-credentials`로 kubectl 연결이 된 상태여야 합니다.

**1. 네임스페이스 생성**

```bash
kubectl apply -f deployment/namespace.yaml
```

**2. Secret 생성 (API 키 주입)**

```bash
kubectl create secret generic sre-agent-secrets \
  --namespace sre-agent \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=QDRANT_URL=http://qdrant-svc:6333 \
  --from-literal=LANGFUSE_PUBLIC_KEY=pk-lf-... \
  --from-literal=LANGFUSE_SECRET_KEY=sk-lf-... \
  --from-literal=LANGFUSE_HOST=https://us.cloud.langfuse.com \
  --from-literal=DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**3. Qdrant + n8n 배포 (영구 볼륨 포함)**

```bash
kubectl apply -f deployment/qdrant.yaml
kubectl apply -f deployment/n8n.yaml

# 볼륨 할당 확인 (STATUS가 Bound면 성공)
kubectl get pvc -n sre-agent
```

**4. 에이전트 이미지 빌드 및 등재**

```bash
# GitHub Container Registry 로그인
echo $CR_PAT | docker login ghcr.io -u <github-username> --password-stdin

# 이미지 빌드 및 푸시
docker build -t ghcr.io/<github-username>/sre-agent:latest .
docker push ghcr.io/<github-username>/sre-agent:latest
```

**5. ArgoCD 설치 및 연동**

```bash
# ArgoCD 설치
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=Available deployment --all -n argocd --timeout=300s

# 초기 비밀번호 확인
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# UI 접속용 포트포워딩
kubectl port-forward svc/argocd-server -n argocd 8081:443
```

**6. GitOps 파이프라인 연결**

```bash
kubectl apply -f deployment/argocd-app.yaml
```

ArgoCD가 GitHub 레포를 감지하여 GKE에 자동 Sync를 시작합니다.

---

## Prometheus 모니터링 설정

**kube-prometheus-stack 설치**

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f deployment/prometheus/values.yaml
```

**알람 규칙 배포**

```bash
kubectl apply -f deployment/prometheus/alert-rules.yaml
```

> `release: kube-prometheus-stack` 레이블이 있어야 Prometheus Operator가 규칙을 인식합니다.

**알람 테스트 (의도적 실패 파드 생성)**

```bash
kubectl apply -f deployment/prometheus/dummy-fail-pod.yaml
# 약 1분 후 AlertManager → /webhook/alertmanager → Discord 알람 확인
```

---

## 서비스 접속 가이드

| 서비스 | 접속 방법 | 주소 |
|--------|-----------|------|
| SRE 에이전트 API | LoadBalancer 외부 IP | `kubectl get svc sre-agent-svc -n sre-agent` |
| ArgoCD UI | port-forward | `kubectl port-forward svc/argocd-server -n argocd 8081:443` → `https://localhost:8081` |
| n8n 워크플로우 | port-forward | `kubectl port-forward svc/n8n-svc 5678:5678 -n sre-agent` → `http://localhost:5678` |
| Prometheus | port-forward | `kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring` → `http://localhost:9090` |
| AlertManager | port-forward | `kubectl port-forward svc/kube-prometheus-stack-alertmanager 9093:9093 -n monitoring` → `http://localhost:9093` |

---

## 초기 지식 시딩 (GKE 최초 배포 후)

GKE에 Qdrant를 처음 배포하면 데이터가 비어 있습니다. 포트포워딩을 통해 로컬에서 데이터를 주입합니다.

```bash
# 터미널 1: Qdrant 포트 열기
kubectl port-forward svc/qdrant-svc 6333:6333 -n sre-agent

# 터미널 2: 시딩 스크립트 실행
export QDRANT_URL=http://localhost:6333
python scripts/seed_data.py
```
