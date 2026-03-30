# Kubernetes(K8s) 핵심 트러블슈팅 상세 가이드 (SRE 세미나 및 실무 운영용)

이 문서는 Kubernetes 클러스터를 프로덕션 환경에서 운영할 때 흔히 마주하는 다양한 파드(Pod), 노드(Node), 그리고 네트워크 계층의 장애 상황을 진단하고 해결하는 상세한 절차와 가이드를 제공합니다.

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

### 1-4. ImagePullBackOff / ErrImagePull
Kubelet 서버가 컨테이너 이미지를 다운로드하지 못할 때 뜹니다.
- **주요 원인 분석**:
  1. Docker 컨테이너 레지스트리(ECR, GCR 등)의 인증 토큰(`imagePullSecrets`) 기간 만료.
  2. `v1.2.` 처럼 이미지 태그 오타가 있거나 실제로 삭제된 이미지.
- **해결 및 대응 방안**:
  인증 정보를 갱신하고 `kubectl create secret docker-registry ...` 명령어로 레지스트리 자격증명을 컨텍스트에 추가해야 합니다.

## 2. 네트워크 및 서비스 디버깅 (Service / Ingress)

### 2-1. 외부에서 Ingress IP나 LoadBalancer IP로 접속이 안 됨 (Connection Refused)
클라우드 인프라는 정상적으로 떴고 IP도 할당됐는데, 웹브라우저에서 접속 에러가 발생합니다.
- **주요 원인 분석**:
  1. 파드가 Liveness/Readiness Probe를 통과하지 못해 K8s Endpoint에 연동되지 않았음. (트래픽 분배 대상이 아님)
  2. Service 매니페스트의 `selector` 라벨(Label)과 파드의 `metadata.labels`가 일치하지 않음.
  3. `targetPort` 와 컨테이너 내부 프로세스가 리스닝하고 있는 포트(Port)가 다름.
- **해결 및 대응 방안**:
  포트 매핑을 먼저 디버깅합니다. 파드 안으로 직접 들어가서 `curl localhost:<port>`가 성공하는지 봅니다.
  `kubectl exec -it <pod-name> -- sh`
  이후 `kubectl get endpoints <service-name>`을 입력했을 때 내부 파드의 K8s 사설 IP 리스트가 존재하는지(매핑 성공 여부) 확인해야 합니다.

### 2-2. 내부 DNS 이름 풀이(Resolve) 오류 
A 파드에서 `http://b-service` 로 요청을 보냈는데 `Name or service not known` 에러가 발생합니다.
- **해결 및 대응 방안**:
  CoreDNS 파드가 정상적으로 Running 중인지 확인합니다 (`kubectl get pods -n kube-system -l k8s-app=kube-dns`). 
  만약 다른 네임스페이스라면 `http://b-service.<namespace>.svc.cluster.local` 형태의 FQDN 전체 도메인 형식을 써주어야 통신이 성사됩니다.

## 3. 노드(Node) 상태 이상 관리

### 3-1. Node NotReady / Unreachable
- 노드 내부의 Kubelet 바이너리가 마스터(Control Plane)에 하트비트를 보내지 못하는 상황입니다.
- 클라우드 환경에서는 주로 Kubelet 데몬 자체가 죽었거나 노드 자체의 메모리가 OOM에 의해 하드락(Hard lock) 상태에 빠진 경우입니다.
- **해결**: GKE/EKS 콘솔에서 해당 워커 노드 인스턴스를 강제 재부팅 시키면, Node Auto-Repair 정책에 의해 새 OS 인스턴스로 자동 교체됩니다.

### 3-2. Evicted 파드 생성 현상
- 노드의 저장 공간(Disk)이 압박을 받을 때 (DiskPressure), Kubelet이 살기 위해 우선순위가 낮은 파드부터 쫓아내며(Eviction) 이 상태의 파드들이 계속 늘어나는 현상입니다.
- **해결**: 로그를 중앙 저장소로 빼서 로컬 용량을 차지하지 못하게 하고, 로컬 파드들의 `emptyDir` 할당량에 리밋을 걸어야 합니다. 삭제 명령어로 찌꺼기를 날립니다:
`kubectl delete pods --field-selector status.reason=Evicted -A`
