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
| `secret.example.yaml` | API 키(OpenAI, Langfuse) 설정 템플릿 |

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
FastAPI 코드를 쿠버네티스에 올리려면 먼저 도커(Docker) 이미지로 빌드하고 컨테이너 저장소(ghcr.io)에 업로드해야 합니다.
```bash
# 1. GitHub Container Registry 로그인 (본인의 Github PAT 토큰 필요)
echo $CR_PAT | docker login ghcr.io -u yongwanjoo --password-stdin

# 2. 이미지 빌드 및 푸시
docker build -t ghcr.io/yongwanjoo/sre-agent:latest .
docker push ghcr.io/yongwanjoo/sre-agent:latest
```

이상이 완료되면 `deployment.yaml` 파일 내의 `image: ` 태그가 올바른지 확인한 뒤, GitOps(ArgoCD) 배포를 진행합니다.

---

## 🚀 GitOps (ArgoCD) 실전 구축 및 연동 가이드

제가 대신 설치해 드린 ArgoCD 인프라를 본인이 직접 처음부터 띄우고 연동하려면 아래 명령어 흐름을 따라주세요. 포트폴리오 면접 등에서 "어떻게 설치하고 연동했냐" 물어볼 때 그대로 대답하실 수 있는 방법입니다!

### 1단계: ArgoCD 컨트롤러 설치 (한 줄 컷)
퍼블릭 오픈소스인 ArgoCD 매니페스트를 GKE 클러스터에 바로 때려넣습니다.
```bash
# 네임스페이스 생성
kubectl create namespace argocd

# ArgoCD 리소스 일괄 배포 
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 모든 파드가 뜰 때까지 잠시 대기
kubectl wait --for=condition=Available deployment --all -n argocd --timeout=300s
```

### 2단계: 초기 비밀번호 풀기 & 포트포워딩
보안상 ArgoCD는 설치될 때 무작위 비밀번호를 생성하여 암호화(Secrets)해 둡니다. 이걸 해독해야 합니다.
```bash
# 1. 초기 비밀번호 (Base64) 디코딩 출력
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo

# 2. 로컬에서 ArgoCD UI에 접속하기 위한 안전한 포트포워딩
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
이제 `https://localhost:8080` 으로 접속하고 **Username: `admin`**, **Password: *(방금 얻은 비밀번호)*** 를 입력합니다.

### 3단계: 우리 레포지토리(SRE 에이전트) 연결하기!
GUI 화면에서 마우스로 클릭해서 앱을 만들 수도 있지만, GitOps 철학에 맞게 'ArgoCD 설정 자체도 코드로' 만들었습니다. 그게 바로 폴더 안의 `argocd-app.yaml` 입니다.
```bash
kubectl apply -f deployment/argocd-app.yaml
```
이걸 치면 K8s에 ArgoCD Application 커스텀 리소스가 생성되고, ArgoCD가 이 사실을 즉시 알아채어 본인의 GitHub 레포지토리와 연동한 뒤 방대한 K8s 모니터링 그래프 창을 자동으로 그려주기 시작합니다.

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

---

## 🏗️ 실 운영 DB에 지식 적재하기 (초기 시딩)

GKE에 Qdrant를 처음 배포하면 데이터가 비어 있습니다. 아래 명령어로 로컬에 있는 테스트 데이터를 클라우드 DB로 밀어 넣을 수 있습니다.

1. **Qdrant 포트 포워딩** (터미널 1):
   ```bash
   kubectl port-forward svc/qdrant-svc 6333:6333 -n sre-agent
   ```

2. **로컬에서 시딩 스크립트 실행** (터미널 2):
   ```bash
   # .env 파일에 OPENAI_API_KEY가 있어야 합니다.
   # QDRANT_URL은 로컬호스트(포트포워딩 중)를 바라봅니다.
   export QDRANT_URL=http://localhost:6333
   python test_data.py
   ```

이제 에이전트가 클라우드에서도 풍부한 지식을 바탕으로 답변할 수 있습니다!
