# deployment/

이 디렉토리는 수집 파이프라인(n8n), 벡터 데이터베이스(Qdrant), API 에이전트 3가지를 **GCP (Google Kubernetes Engine) 내부망에 완벽히 격리 및 배포**하는 Kubernetes + ArgoCD 설정 파일들입니다.

---

## 아키텍처 (GCP GKE)

```
[인터넷 통신]                    [GKE 클러스터 내부 (sre-agent Ns)]
 LoadBalancer (80)     →        API 에이전트 (Pod)
                           (인터넷 차단 내부통신 ↓ API 호출: http://qdrant-svc:6333)
                              Qdrant DB (Pod) ←동적 마운트→ [GCP 영구 디스크 5GB]
                           (인터넷 차단 내부통신 ↑ 문서 적재: http://qdrant-svc:6333)
 Port-Forward (5678)   →        n8n 파이프라인 (Pod) ←동적 마운트→ [GCP 영구 디스크 5GB]
```

## 파일 설명

| 파일 | 역할 |
|------|------|
| `namespace.yaml` | K8s 네임스페이스 생성 (`sre-agent`) |
| `qdrant.yaml` | Qdrant DB 파드 및 영구 볼륨 연결 (GCP Persistent Disk) |
| `n8n.yaml` | n8n 자동화 툴 파드 및 영구 볼륨 연결 (GCP Persistent Disk) |
| `deployment.yaml` | 에이전트 파드 배포 설정 |
| `service.yaml` | 에이전트 외부 공개용 LoadBalancer 설정 |
| `argocd-app.yaml` | GitOps 배포 파이프라인 구성 |

---

## 🚀 GCP GKE 배포 순서 (최초 1회)

> 전제: GCP 콘솔에서 GKE 클러스터(Standard 또는 Autopilot)가 생성되어 있고, 터미널에서 `gcloud container clusters get-credentials` 로 k8s 연결이 된 상태여야 합니다.

### Step 1. Namespace 생성
```bash
kubectl apply -f deployment/namespace.yaml
```

### Step 2. Secret 생성 (API 키 등 안전한 등록)
로컬 `.env`에 있는 키들을 GCP 안으로 주입합니다.
```bash
kubectl create secret generic sre-agent-secrets \
  --namespace sre-agent \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=QDRANT_URL=http://qdrant-svc:6333 \     # 핵심: GKE 내부 DNS 라우팅
  --from-literal=LANGFUSE_PUBLIC_KEY=pk-lf-... \
  --from-literal=LANGFUSE_SECRET_KEY=sk-lf-...
```

### Step 3. 인프라 볼륨(Qdrant, n8n) 배포
GKE 환경에서는 스토리지 클래스가 자동 연동되므로 yaml만 적용하면 구글 스토리지가 즉시 할당(Bound)됩니다.
```bash
kubectl apply -f deployment/qdrant.yaml
kubectl apply -f deployment/n8n.yaml

# 볼륨 할당 확인 (STATUS가 Bound면 성공)
kubectl get pvc -n sre-agent
```

### Step 4. 에이전트 매니페스트 배포 준비 및 배포
`deployment.yaml` 파일 내의 `image: ` 태그와 `argocd-app.yaml`의 `repoURL:` 값들을 본인의 GitHub 주소로 수정한 뒤, ArgoCD나 수동 적용을 진행합니다.
```bash
# ArgoCD 연동을 하려면
kubectl apply -f deployment/argocd-app.yaml

# ArgoCD 없이 직접 수동 배포하려면
kubectl apply -f deployment/deployment.yaml
kubectl apply -f deployment/service.yaml
```

---

## 🛠 서비스 접속 가이드

**1. 에이전트 API (챗봇) 접속하기**
> 에이전트는 LoadBalancer 타입으로 배포되어 인터넷을 통해 누구나 접근 가능합니다. 외부 IP가 발급될 때까지 1~2분 소요됩니다.
```bash
# EXTERNAL-IP 주소가 할당되면 브라우저/cURL에서 해당 IP로 접속
kubectl get svc sre-agent-svc -n sre-agent
```

**2. n8n 워크플로우 화면 접속하기 (보안 접속)**
> n8n은 민감한 파이프라인 툴입니다. GKE에 올렸기 때문에 외부에서 함부로 해킹하지 못하게 내부망(ClusterIP)으로 차단했습니다.
> 관리자인 나침만이 접근할 땐 아래 명령어로 로컬 PC 포트를 뚫어줍니다.
```bash
kubectl port-forward svc/n8n-svc 5678:5678 -n sre-agent
```
이후 `http://localhost:5678` 브라우저 창으로 접속합니다! (창을 끄면 차단됨)
