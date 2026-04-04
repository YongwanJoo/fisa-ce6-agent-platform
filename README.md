# 우리 FIS 아카데미 2차 기술 세미나 - AgentOps: 지능형 SRE 에이전트 플랫폼

> **AgentOps** — ArgoCD / Kubernetes 운영 중 발생하는 장애를 실시간 감지·분석하고, Discord로 해결책을 리포트하는 **지능형 SRE 에이전트 플랫폼**입니다.
> 고도화된 **Traefik 인그레스, HA 파드 구성, 정제된 모니터링 알람**이 통합된 인프라 환경을 지향합니다.

![플랫폼 전체 아키텍처](images/전체%20아키텍처.png)

GCP GKE + Traefik Ingress + GitOps(ArgoCD) + n8n 지식 자동화

---

## 목차
1. [플랫폼 아키텍처 (논리/물리)](#플랫폼-아키텍처-논리물리)
2. [상세 구성 요소 및 역할](#상세-구성-요소-및-역할)
3. [AgentOps 파이프라인](#agentops-파이프라인)
4. [네트워크 및 보안 설계](#네트워크-및-보안-설계)
5. [운영 및 모니터링](#운영-및-모니터링)
6. [트러블슈팅 및 가이드](#트러블슈팅-및-가이드)

---

## 쿠버네티스 아키텍처 (논리/물리)

시스템의 서비스 흐름(논리)과 실제 서버 기반의 배치(물리)를 통합하여 관리합니다.

### 1.1 논리 아키텍처 (Logical Overview)
![플랫폼 논리 아키텍처](images/쿠버네티스%20논리%20아키텍처.png)
- **설명**: 네임스페이스 기반의 서비스 격리와 트래픽 라우팅, 그리고 지식 검색(RAG) 흐름을 보여줍니다.
- **특징**: n8n을 통한 자동 지식 적재와 SRE 에이전트의 분석 루프가 핵심입니다.

### 1.2 물리 아키텍처 (Physical Overview)
![쿠버네티스 물리 아키텍처](images/쿠버네티스%20물리%20아키텍처.png)
- **설명**: GKE 클러스터 내 2개의 워커 노드에 파드들이 어떻게 분산 배치되어 있는지를 보여줍니다.
- **특징**: `podAntiAffinity`를 통한 에이전트 분산과 각 파드별 전용 GCP Persistent Disk(PD) 연결을 시각화했습니다.

---

## 상세 구성 요소 및 역할

### 1. Ingress & Traffic Control
- **Traefik v3**: 
    - 클러스터 외부 진입을 관리하는 현대적인 리버스 프록시 모든 서비스 트레픽을 단일 엔트리포인트로 통합
    - 전용 대시보드를 통해 실시간 라우팅 상태를 시각적으로 모니터링

### 2. SRE Discovery Agent
- **FastAPI / LangGraph**: 
    - 에이전트의 중추 역할을 수행하며 Prometheus 장애 컨텍스트를 분석하여 대응
    - 파드 2개(HA) 구성으로 인프라 장애 시에도 분석 업무를 지속

### 3. Knowledge Storage & Pipeline
- **Qdrant (Vector DB)**: K8s 트러블슈팅 지식을 고차원 벡터로 저장하며 영구 디스크(PD)로 데이터를 보호
- **n8n Automation**: 깃허브 레포지토리의 `data/` 폴더를 주기적으로 크롤링하여 최신 지식을 Qdrant에 적재

### 4. Observability Stack
- **Prometheus / AlertManager**: 실시간 메트릭 수집 및 핵심 장애 발생 시 SRE 에이전트 트리거를 담당
- **Grafana**: 전용 대시보드(ID: 3119)를 통해 클러스터 리소스 사용량을 실시간 관측

---

## AgentOps 파이프라인

본 플랫폼은 세 가지 핵심 루프를 통해 자동화된 운영 환경을 완성합니다.

![파이프라인 아키텍처](images/파이프라인.png)

1.  **DevOps Loop**: CI(Eval) -> ArgoCD를 통한 안정적인 무중단 배포 루프
2.  **Knowledge Loop**: n8n -> Qdrant 지식 데이터 정시 적재 루프
3.  **Incident Loop**: 장애 감지 -> 분석(RAG) -> 소통(Discord) 대응 루프

---

## 네트워크 및 보안 설계

서비스 안정성과 데이터 보안을 위해 트래픽 접근 권한을 계층적으로 분리했습니다.

![네트워크 트래픽 흐름](images/네트워크%20트래픽.png)

| 컴포넌트 | 서비스 타입 | 접근 방식 | 보안 이유 |
| :--- | :--- | :--- | :--- |
| **Traefik Ingress** | `LoadBalancer` | 인터넷 공인 IP (80/443) | 모든 트래픽의 보안 단일 관문 (EntryPoint) |
| **SRE Agent API** | `ClusterIP` | Traefik / IngressRoute | 인그레스를 통한 L7 라우팅 및 인증 계층 적용 |
| **Admin UI (Grafana, n8n)** | `ClusterIP` | `kubectl port-forward` | 보안상 인증된 관리자만 로컬 세션으로 접근 |

---

## 운영 및 모니터링

### 스마트 알림 정책
GKE 환경의 노이즈 알람을 필터링하고 실제 조치가 필요한 항목만 전달합니다.
- **Watchdog 필터링**: 불필요한 테스트 알람 자동 차단
- **핵심 장애 감지**: NodeDown, PodCrashLoop 등 크리티컬 이슈 집중 모니터링

### Grafana 대시보드
- **ID**: 3119 (Kubernetes Cluster Monitoring)
- **계정**: `admin` / `1q2w3e4r!@` (설치 시 자동 반영)

---

## 트러블슈팅 및 가이드

플랫폼 구축 및 운영 과정에서 발생한 주요 기술적 이슈와 해결 방안입니다.

### 1. 인프라 및 GKE 운영 (Infrastructure)
- **GKE 관리형 컴포넌트 허위 알람 (TargetDown)**: GKE가 관리하는 ControllerManager, Scheduler 등의 메트릭 접근 불가로 인한 알람입니다. `deployment/prometheus/values.yaml`에서 해당 항목의 모니터링을 `false`로 설정하여 해결했습니다.
- **서비스 가용성 및 아키텍처 불일치 (arm64 vs amd64)**: 로컬(Mac M-series)과 클러스터(GCP) 간 아키텍처 불일치 문제는 Docker Multi-stage build 시 플랫폼을 명시하여 해결했으며, `podAntiAffinity`를 통해 파드를 여러 노드에 분산 배치하여 고가용성을 확보했습니다.

### 2. GitOps 및 배포 파이프라인 (ArgoCD)
- **ArgoCD 동기화 지연 및 ComparisonError**: 매니페스트 오탈자나 이미지 태그 누락 등으로 인한 동기화 실패 시, `Self-Heal` 옵션을 활성화하고 `kubectl describe`를 통해 상태를 교정하여 해결했습니다.

### 3. AI 에이전트 및 RAG 파이프라인 (AI/RAG)
- **에이전트 답변 품질 저하 및 낮은 Eval 점수**: 단순 키워드 검색의 한계를 극복하기 위해 **쿼리 재작성(Rewriting)** 루프를 도입하고, **LLM-as-a-Judge** 방식을 통해 정성적인 평가 체계를 구축하여 답변 정확도를 높였습니다.
- **벡터 DB(Qdrant) 데이터 유실**: 컨테이너 재시작 시 데이터가 사라지는 문제를 방지하기 위해 GCP Persistent Disk(PD)를 PVC로 연결하고, `scripts/seed_data.py`를 통해 초기 지식 자동 복구 메커니즘을 마련했습니다.

### 4. 관찰성 체계 (Observability)
- **PrometheusRule 인식 실패 (Label Issue)**: 규칙 파일에 `release: kube-prometheus-stack` 레이블이 누락되어 발생하는 이슈를 레이블 추가를 통해 해결했습니다.
- **Discord 알람 전송 실패**: Webhook URL 보안 관리 방식을 Secret으로 변경하고, AlertManager 데이터 전송 규격에 맞게 에이전트 스키마를 정밀 조정하여 해결했습니다.