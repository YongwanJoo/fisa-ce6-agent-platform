# Kubernetes(K8s) 핵심 트러블슈팅 상세 가이드 (AgentOps Knowledge Base)

> **Metadata**
> - **Category**: Infrastructure / Orchestration
> - **Keywords**: Pod, Node, Network, PVC, PDB, CNI
> - **Version**: 1.2.0 (SRE Seminar Edition)

이 문서는 Kubernetes 클러스터를 프로덕션 환경에서 운영할 때 흔히 마주하는 다양한 파드(Pod), 노드(Node), 그리고 네트워크 계층의 장애 상황을 진단하고 해결하는 상세한 절차와 가이드를 제공합니다.

---

## 1. 파드(Pod) 라이프사이클 및 장애 디버깅

### 1-1. CrashLoopBackOff 상태
컨테이너가 기동되었으나 내부 프로세스가 정상적으로 동작하지 못하고 계속 종료되어 재시작(Restart) 루프에 빠진 상태입니다.
- **주요 원인 분석**:
  1. 애플리케이션 코드가 초기화 과정에서 익셉션을 던짐 (DB 접속 실패, 필수 환경 변수 누락 등)
  2. 컨테이너가 실행할 Entrypoint 쉘 스크립트 오타 또는 권한(`chmod +x`) 누락
  3. Liveness Probe(활성 상태 검사)에 응답하지 못해 Kubelet이 강제로 재시작시킴
- **해결 및 대응 방안**:
  가장 먼저 해야 할 일은 컨테이너가 죽기 직전의 마지막 로그를 확인하는 것입니다.
  `kubectl logs <pod-name> -n <namespace> --previous`
  이 로그가 비어 있다면 이벤트 탭을 확인합니다.
  `kubectl describe pod <pod-name> -n <namespace>`

### 1-2. OOMKilled (Out Of Memory)
커널 레벨의 `OOM Killer`가 메모리를 초과 사용한 프로세스를 강제로 죽였을 때 발생합니다.
- **주요 원인 분석**:
  매니페스트(`deployment.yaml`)에 정의된 `resources.limits.memory` 값보다 실제 컨테이너 내 프로세스(Java 힙 메모리, Node.js GC 메모리 누수 등)가 더 많은 메모리를 요구한 경우입니다.
- **해결 및 대응 방안**:
  1. 즉각적인 대응: Deployment의 `limits.memory` 값을 증설하여(예: 512Mi -> 1Gi) 일시적으로 서비스를 살립니다.
  2. 근본적 해결: 애플리케이션 프레임워크에 맞는 메모리 튜닝 플래그를 추가합니다 (Java의 경우 `-XX:MaxRAMPercentage=80.0`).
  3. 리소스 사용량 추적: `kubectl top pod` 또는 Prometheus/Grafana 대시보드를 통해 지속적으로 리소스 누수를 모니터링합니다.

### 1-3. Pending 상태 영구 대기
스케줄러에 의해 노드에 할당(Assign)되지 못하고 허공에 떠 있는 상태입니다.
- **주요 원인 분석**:
  1. CPU/RAM 리소스가 부족하여 클러스터 내 어떤 노드도 이 파드를 수용할 수 없음.
  2. 노드셀렉터(NodeSelector) 나 Taint/Toleration이 잘못 매핑되어 갈 곳을 잃음.
  3. PersistentVolumeClaim(PVC)이 바인딩(Bind)되지 않음.
- **해결 및 대응 방안**:
  `kubectl describe pod <pod-name>` 으로 `Events:` 탭의 스케줄링 실패 사유를 확인합니다. `0/3 nodes are available: 3 Insufficient cpu.` 와 같은 에러가 뜬다면 클러스터 오토스케일러 연동을 확인하거나 수동으로 노드를 스케일업(증설)해야 합니다.

### 1-4. PodDisruptionBudget (PDB)로 인한 노드 드레인 실패
클러스터 업그레이드나 노드 교체(Drain) 시 노드가 비워지지 않고 멈춰있는 현상입니다.
- **상세**: `PDB`가 `minAvailable: 1` 로 설정되어 있는데 파드가 1개뿐인 경우, K8s는 서비스 가용성을 위해 해당 노드에서 파드를 쫓아내지 못하게 막습니다.
- **해결**: 임시로 PDB를 삭제하거나 Deployment의 Replicas를 일시적으로 늘려 가용 파드 수를 확보한 뒤 노드를 비워야 합니다.

---

## 2. 네트워크 및 서비스 디버깅 (Service / Ingress)

### 2-1. 외부 접속 불가 (Connection Refused / Gateway Timeout)
- **점검 순서**:
  1. **Endpoints 확인**: `kubectl get ep <svc-name>` 명령으로 파드 IP가 서비스에 정상 연동됐는지 확인. (Readiness Probe 실패 시 여기서 누락됨)
  2. **Port Conflict**: `targetPort`와 애플리케이션 리슨 포트가 일치하는지 확인.
  3. **NetworkPolicy**: 네임스페이스 간 통신을 차단하는 네트워킹 정책이 있는지 확인.

### 2-2. 내부 DNS 이름 풀이(Resolve) 오류 
A 파드에서 `http://b-service` 로 요청을 보냈는데 `Name or service not known` 에러가 발생합니다.
- **해결**: CoreDNS 파드 상태를 점검하고, 타 네임스페이스 통신 시에는 `b-service.<ns>.svc.cluster.local` 전체 도메인(FQDN)을 사용하십시오.

### 2-3. 제어 평면(Control Plane) 구성 요소 장애 (KubeProxy, Scheduler 등)
- **에러명**: `KubeProxyDown`, `KubeSchedulerDown`, `KubeControllerManagerDown`
- **주요 원인**: 
  1. GKE/EKS 등 관리형 쿠버네티스의 마스터 노드와 프로메테우스 간의 통신 장애.
  2. 마스터 컴포넌트가 리소스 부족으로 인해 비정상 종료되었거나 재시작 중인 상태.
- **분석 및 해결**:
  1. **상태 확인**: `kubectl get pods -n kube-system` 명령으로 해당 컴포넌트가 Running 인지 확인하십시오.
  2. **GCP 콘솔 확인**: GKE 대시보드에서 '제어 평면 상태'가 '정상'인지 확인하고, 업그레이드 중인지 체크하십시오.
  3. **인증 갱신**: 가끔 API 서버 통신 인증이 깨졌을 때 발생하므로 `gcloud container clusters get-credentials` 명령을 통해 인증 세션을 리프레시하십시오.

### 2-4. TargetDown (CoreDNS / Monitoring Targets)
- **증상**: 프로메테우스에서 특정 타겟(주로 CoreDNS)의 메트릭 수집이 100% 실패함.
- **해결**: 
  1. CoreDNS 파드가 모두 죽었는지 확인하십시오.
  2. **즉각 조치**: `kubectl rollout restart deployment coredns -n kube-system` 명령으로 DNS 서버를 재시작하여 인코딩 문제를 해결할 수 있습니다.
  3. 서비스 엔드포인트(`kubectl get ep coredns -n kube-system`)가 파드 IP를 제대로 물고 있는지 확인하십시오.

---

## 3. 스토리지(Storage) 및 노드 장애

### 3-1. Multi-Attach Error (PVC 마운트 실패)
- **증상**: 파드가 다른 노드로 옮겨갔는데, 이전 노드에서 볼륨 해제(Detach)가 안 되어 새 노드에서 마운트를 못 하고 대기하는 상태.
- **해결**: 이전 노드의 볼륨 어태치먼트(VolumeAttachment) 리소스를 강제로 정리하거나, 클라우드 콘솔(AWS EBS/GCP PD)에서 수동으로 Detach 시켜야 합니다.

### 3-2. Node NotReady (Kubelet 멈춤)
- **해결**: GKE 환경 등에서는 `Node Auto-Repair`가 작동하지만, 수동 대응 시에는 SSH 접속 후 `systemctl restart kubelet` 또는 노드 인스턴스 재부팅이 필요합니다.

---

## 4. AgentOps 운영 팁 (SRE 에이전트 활용)
- **로그 분석**: 에이전트에게 `kubectl logs --previous` 결과를 전달하여 종료 직전의 Stack Trace를 분석 요청하십시오.
- **이벤트 전파**: `kubectl get events --sort-by='.lastTimestamp'` 명령 결과를 에이전트에게 주어 시간순 발생 장애를 브리핑받으십시오.

