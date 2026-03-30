# fisa-ce6-agent-platform

> **AgentOps** — ArgoCD / Kubernetes 운영 중 발생하는 에러를 자동 감지·분석하고, Discord로 해결책을 리포트하는 SRE 에이전트 플랫폼입니다.
> 단순 RAG 챗봇이 아닌, **에이전트 배포·지식 자동화·품질 평가·실시간 관측**이 통합된 완전 관리형 인프라를 구현합니다.

GCP GKE + GitOps(ArgoCD) + n8n 클라우드 자동화 구조 적용

---

## 목차

1. [전체 아키텍처](#전체-아키텍처)
2. [디렉토리 구조](#디렉토리-구조)
3. [주요 기능](#주요-기능)
4. [기술 스택](#기술-스택)
5. [빠른 시작 (로컬)](#빠른-시작-로컬)
6. [GCP 배포](#gcp-배포)
7. [AgentOps 파이프라인](#agentops-파이프라인)
8. [네트워크 보안 설계](#네트워크-보안-설계)
9. [트러블슈팅](#트러블슈팅)

---

## 전체 아키텍처

```
[외부 / 사용자]                      [GCP GKE — sre-agent 네임스페이스]
                                        ┌─────────────────────────────────┐
 LoadBalancer (80)  ───────────────►   │  SRE Agent (FastAPI + LangGraph) │
                                        │    ↕ ClusterIP 내부 통신          │
 AlertManager Webhook ────────────►   │  Qdrant DB ←── GCP PD 5GB        │
                                        │  n8n Pipeline ←── GCP PD 5GB    │
 kubectl port-forward (관리자 전용) ──► │  Prometheus + AlertManager        │
                                        └─────────────────────────────────┘
                                                     ↕
                                           Langfuse Cloud (관측)
                                           Discord (장애 리포트)
```

---

## 디렉토리 구조

```
fisa-ce6-agent-platform/
├── agent/              # FastAPI 서버 + LangGraph 에이전트 핵심 코드
│   ├── api.py          # REST API 엔드포인트 (/query, /health, /webhook/alertmanager)
│   ├── graph.py        # LangGraph 에이전트 상태 머신 (전체 흐름 제어)
│   ├── llm.py          # LLM 호출 — 의도 분류 / 쿼리 재작성 / 답변 생성
│   └── retriever.py    # Qdrant 벡터 검색 (의도에 따라 컬렉션 선택)
├── data/               # 에이전트 지식 원본 문서 보관소 (로컬 수동 적재용)
│   ├── k8s_troubleshooting.md
│   ├── argocd_troubleshooting.md
│   └── terraform_troubleshooting.md
├── deployment/         # GKE 배포용 Kubernetes 매니페스트
│   ├── prometheus/     # Prometheus 알람 규칙 및 AlertManager 설정
│   ├── deployment.yaml
│   ├── qdrant.yaml
│   ├── n8n.yaml
│   └── argocd-app.yaml
├── observability/      # 관측(Langfuse) 및 품질 평가(Eval) 코드
│   ├── eval.py         # CI 자동 평가 스크립트 (점수 미달 시 배포 차단)
│   ├── langfuse_setup.py
│   └── golden_set.json # 평가 기준 질문-정답 셋
├── pipeline/           # n8n 자동화 워크플로우 백업 및 가이드
├── scripts/            # 로컬 운영 스크립트
│   ├── seed_data.py    # Qdrant 초기 지식 시딩
│   └── run_agent.py    # 에이전트 수동 테스트 실행
├── terraform/          # GKE 클러스터 인프라 코드 (IaC)
│   ├── main.tf         # GKE 클러스터 + 노드 풀 정의
│   ├── variables.tf
│   └── terraform.tfvars.template
└── qdrant_data/        # 로컬 Qdrant 벡터 데이터 저장소 (로컬 테스트 전용)
```

---

## 주요 기능

### 능동형 장애 대응

Prometheus가 `CrashLoopBackOff`, `OOMKilled` 등의 지표를 감지하면 AlertManager가 SRE 에이전트의 `/webhook/alertmanager`로 Webhook을 전송합니다. 에이전트는 LangGraph를 가동해 Qdrant 지식 베이스를 검색하고, 원인 분석 + `kubectl` 디버깅 명령어가 포함된 브리핑 리포트를 Discord 채널에 즉시 전송합니다.

```
Prometheus ──► AlertManager ──► SRE Agent ──► Qdrant 검색
                                     │
                                     └──► Discord (원인 + 조치 명령어)
```

### 지식 자동화

n8n Pod가 매일 새벽 `kubernetes.io` 공식 문서를 자동으로 크롤링·임베딩해 Qdrant에 적재합니다. 로컬 노트북이 꺼져 있어도 클라우드 내부에서 지식이 최신화됩니다. GCP 영구 디스크(PD)를 마운트해 파드 재시작 시에도 벡터 데이터가 유실되지 않습니다.

### 품질 게이트 (Eval in CI)

프롬프트 또는 에이전트 로직을 변경해 GitHub에 Push하면, CI가 자동으로 `observability/eval.py`를 실행합니다. 평균 점수가 0.75 미만이면 Docker 이미지 빌드 자체가 차단되므로, 품질이 낮아진 에이전트는 절대 운영 환경에 배포되지 않습니다.

---

## 기술 스택

| 레이어 | 기술 | 역할 |
|--------|------|------|
| **에이전트 프레임워크** | LangGraph 0.2.x | 노드 기반 에이전트 상태 머신, Tool 호출 |
| **LLM** | OpenAI GPT-4o-mini | 에러 분석 및 해결책 생성 |
| **벡터 DB** | Qdrant v1.13.x | K8s·ArgoCD 문서 임베딩 저장 및 검색 |
| **데이터 파이프라인** | n8n (latest) | 공식 문서 자동 크롤링·임베딩 스케줄링 |
| **에이전트 관측** | Langfuse 2.x | LLM 비용·레이턴시·품질 실시간 트레이싱 |
| **인프라 모니터링** | Prometheus + AlertManager | Pod 상태 감시 및 Webhook 트리거 |
| **GitOps 배포** | ArgoCD (latest) | Git 변경 감지 → GKE 자동 Sync |
| **클라우드 인프라** | GCP GKE (Standard/Autopilot) | 컨테이너 오케스트레이션 |
| **IaC** | Terraform | GKE 클러스터 인프라 코드화 |
| **CI/CD** | GitHub Actions + GHCR | Eval → 빌드 → 이미지 등재 파이프라인 |

---

## 빠른 시작 (로컬)

> 전체 GCP 배포 없이 에이전트 코드만 로컬에서 실행하는 방법입니다.

**1. 레포 클론 및 환경 설정**

```bash
git clone https://github.com/nyongwan/fisa-ce6-agent-platform.git
cd fisa-ce6-agent-platform

cp .env.example .env
# .env에서 OPENAI_API_KEY 값을 채워주세요

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. 로컬 Qdrant 실행**

```bash
podman run -d --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/qdrant_data:/qdrant/storage:Z \
  docker.io/qdrant/qdrant:v1.17.1
```

`http://localhost:6333/dashboard` 에 접속되면 정상입니다.

**3. 에이전트 실행**

```bash
# CLI 모드
python main.py

# API 서버 모드 (FastAPI)
uvicorn agent.api:app --reload --port 8000
```

**4. 에이전트에 지식 주입 (선택)**

```bash
# 로컬 Qdrant에 테스트 데이터 적재
python scripts/seed_data.py
```

---

## GCP 배포

전체 GKE 인프라를 한 번에 띄우는 방법은 각 가이드를 참고하세요.

- [GCP GKE 전체 배포 가이드](./deployment/README.md)
- [n8n 자동 파이프라인 구성 가이드](./pipeline/README.md)
- [Terraform GKE 클러스터 프로비저닝](./terraform/)

### Terraform으로 GKE 클러스터 생성

```bash
cd terraform
cp terraform.tfvars.template terraform.tfvars
# terraform.tfvars에 project_id, region, zone 입력

terraform init
terraform apply
```

> e2-standard-2 노드 2대(2 vCPU / 8GB RAM)로 구성된 GKE 클러스터가 생성됩니다.

---

## AgentOps 파이프라인

```
코드 / 프롬프트 변경
       │
  GitHub Push
       │
  GitHub Actions
  ├── Qdrant Sidecar 기동 + 테스트 데이터 주입 (test_data.py)
  ├── Eval 스크립트 실행 — 평균 점수 0.75 이상?
  │     ├── 통과 → Docker 이미지 빌드 → GHCR 등재
  │     └── 실패 → 배포 즉시 차단 ✗
       │
  ArgoCD — Git 변경 감지 → GKE Sync
       │
  Langfuse — 배포 후 실시간 관측
  (비용 / 레이턴시 / 답변 품질)
```

---

## 네트워크 보안 설계

외부에 노출되는 컴포넌트를 최소화하는 것을 원칙으로 설계했습니다.

| 컴포넌트 | 서비스 타입 | 접근 방식 | 이유 |
|----------|-------------|-----------|------|
| SRE 에이전트 API | `LoadBalancer` | 인터넷 공인 IP (80포트) | 사용자 및 AlertManager가 직접 호출해야 하므로 유일하게 외부 개방 |
| Qdrant DB | `ClusterIP` | K8s 내부 DNS만 허용 (`http://qdrant-svc:6333`) | 핵심 지식 베이스이므로 외부 접근 원천 차단 |
| n8n / ArgoCD | `ClusterIP` | `kubectl port-forward` (관리자 전용) | 파이프라인 조작 방지, 로컬 인증된 관리자만 UI 접근 가능 |

---

## 트러블슈팅

운영 중 마주친 주요 문제와 해결 방법입니다.

**CI에서 Eval 점수가 0점으로 나오는 문제**

CI 환경에는 Qdrant DB가 비어 있어 에이전트가 아무것도 검색하지 못하는 상태로 평가가 진행됩니다. `.github/workflows/ci.yml`에 Qdrant Sidecar 서비스를 추가하고, 평가 직전 `test_data.py`를 실행해 데이터를 자동 주입하도록 개선했습니다.

**GKE 배포 후 답변 품질 저하**

새로 배포된 Qdrant는 지식이 없는 초기 상태입니다. `kubectl port-forward`로 클라우드 Qdrant에 연결한 뒤 `test_data.py`를 실행해 Golden Set 기반 초기 지식을 수동 시딩합니다.

**PrometheusRule이 대시보드에 나타나지 않는 문제**

Prometheus Operator는 `ruleSelector`에 정의된 레이블이 있는 리소스만 수집합니다. `PrometheusRule` 메타데이터에 `release: kube-prometheus-stack` 레이블을 명시하면 해결됩니다.

**ArgoCD Self-Heal로 인한 Secret 원복 문제**

ArgoCD의 자동 복구 기능이 활성화된 상태에서 `kubectl apply`로 Secret을 수정하면 몇 초 뒤 Git 상태로 강제 동기화됩니다. GitHub Actions Secret을 수정해 파이프라인으로 배포하거나, 테스트 시에는 ArgoCD Auto-Sync를 일시 비활성화합니다.

**Langfuse 401 Unauthorized 및 트레이싱 중단**

`LANGFUSE_HOST`가 실제 계정의 리전과 불일치하거나 시크릿 업데이트가 실패한 경우 발생합니다. 정확한 리전 주소(예: `https://us.cloud.langfuse.com`)를 확인하고, K8s Secret을 재생성한 뒤 `rollout restart`로 최신 환경변수를 반영합니다.

**AlertManager Webhook 발송 지연 (Pending State)**

`for: 1m` 설정으로 인해 파드가 죽어도 즉시 알람이 발송되지 않습니다. 장애가 1분 이상 지속될 때만 Firing 상태로 전환되는 것은 단발성 이벤트(Flapping) 필터링을 위한 의도된 설계입니다. 테스트 시에는 1분 이상의 관찰 시간을 확보해야 합니다.

---

## 참고 자료

- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [LangGraph Agentic RAG 튜토리얼](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_agentic_rag/)
- [Langfuse 공식 문서](https://langfuse.com/docs)
- [Qdrant 공식 문서](https://qdrant.tech/documentation/)
- [ArgoCD 공식 문서](https://argo-cd.readthedocs.io/)