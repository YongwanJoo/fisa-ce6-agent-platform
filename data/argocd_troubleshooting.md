# ArgoCD 심층 동기화 및 장애 대응 매뉴얼 (SRE 실무 가이드용)

ArgoCD는 GitOps의 원칙을 단일 진실의 근원(Single Source of Truth)으로 구현하는 강력한 쿠버네티스 CD 도구이지만, 그 구조가 선언적이므로 배포 시 다양한 상태 오류(Sync, Health 문제)가 발생할 수 있습니다. 

## 1. Application 동기화(Sync) 상태의 불일치

### 1-1. OutOfSync (동기화 벗어남) 현상
Git 저장소의 YAML 내용과 쿠버네티스 클러스터의 실제 상태가 어긋났을 때 나타나는 가장 대표적인 노란색 경고입니다.
- **주요 원인(Root Cause)**:
  1. SRE나 개발자가 K8s 콘솔이나 터미널을 통해 `kubectl apply`를 수동으로 쳐서 운영환경을 직접 조작한 경우.
  2. K8s 내부의 Mutating Webhook Controller (예: Istio Proxy 인젝션이나 Cert-Manager 등)가 배포가 들어가자마자 자동으로 Config를 바꿔치기 한 경우.
  3. Horizontal Pod Autoscaler(HPA) 가 `replicas` 수를 동적으로 변경했는데, Git에는 아직 구버전의 숫자(예: `replicas: 1`) 가 박혀 있는 경우.
- **트러블슈팅 및 해결**:
  ArgoCD에서 `Diff` 뷰를 열면 어떤 스펙이 다른지 하이라이트 됩니다.
  HPA처럼 시스템상 K8s가 자동으로 바꿔야만 하는 값 (예: replicas) 때문에 자꾸 OutOfSync가 뜬다면, ArgoCD Application 설정(`ignoreDifferences`)에 예외 규칙을 넣어 해당 필드만 ArgoCD가 무시하도록 세팅해야 합니다.
  ```yaml
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/replicas
  ```

### 1-2. Sync Failed (동기화 실패)
배포 버튼을 눌렀음에도 애플리케이션의 뼈대 자체가 K8s에 생성되지 못하고 동기화 작업이 에러 코드와 함께 중단됩니다.
- **주요 원인(Root Cause)**:
  1. 클러스터에 존재하지 않는 Custom Resource Definition(CRD) 모델을 띄우려고 시도했음.
  2. 네임스페이스 자체를 띄운 적이 없는데 띄우려는 앱이 해당 네임스페이스를 참조하고 있음.
  3. 구문(Syntax) 에러: YAML 띄어쓰기 린트 오류 등.
- **트러블슈팅 및 해결**:
  에러 메시지를 보고 ArgoCD가 실행하는 `kubectl apply` 결과의 린트 및 유효성(Validation) 오류를 파악합니다. Git 코드에서 오타를 제거하고 Push하면 3분 주기로 재동기화(Polling) 되어 자동 복구됩니다.

## 2. Health 확인 불가 및 Degraded 에러

### 2-1. Degraded (저하됨 / 레드 알람)
파드나 리소스가 K8s 내부에 무사히 들어왔음에도 불구하고, 애플리케이션이 스스로 구동되지 못하고 퍼진 상태를 의미합니다.
- **주요 원인(Root Cause)**:
  1. 파드의 `CrashLoopBackOff`, `ErrImagePull` 등 K8s 하위 노드 종속적 에러.
  2. K8s `Job`이나 `CronJob`을 배포했는데 내부 스크립트가 실행 도중 실패(Failed) 상태로 종료되었음.
- **트러블슈팅 및 해결**:
  ArgoCD 트리의 맨 마지막 노드(주로 붉은색 깨진 하트 모양)를 클릭하여 `Logs` 및 `Events` 탭을 열고, 컨테이너 왜 죽었는지 근본 원인을 K8s 로그로 직접 추적해야 합니다.

### 2-2. Health Unknown / Progressing (진행중 멈춤)
배포가 완료되지 못한 채 파란 톱니바퀴 모형(Progressing)이 계속 돌고 있거나 물음표(Unknown)로 뜹니다.
- **주요 원인(Root Cause)**:
  1. (Unknown 상태): Custom Resource(CRD) 리소스인데 ArgoCD가 이 커스텀 리소스의 성공/실패 여부를 판독하는 법을 몰라서 상태를 `알 수 없음`으로 방치하는 경우입니다.
  2. (Progressing 상태): Deployment의 `Rolling Update` 전략을 실행 중인데 신버전 파드가 영원히 Readiness Probe (활성 점검)를 통과하지 못해 트래픽을 주지 않고 대기하는 상태(Stuck).
- **트러블슈팅 및 해결**:
  CRD Health 검사를 고치고자 할 경우 ArgoCD의 `argocd-cm` ConfigMap에 Custom Health Check Lua Script를 주입해주면 ArgoCD가 똑똑하게 이를 파싱하여 Healthy 상태로 변경해 줍니다. 프로그레싱 버그일 경우 K8s 로드밸런서와 Liveness 점검 URL 포트가 일치하는지 재확인합니다.

## 3. 권한 및 보안 관련 에러 (RBAC Issues)

### 3-1. Sync Error: forbidden user system:serviceaccount:argocd...
- **원인**: ArgoCD에 K8s 클러스터 내 다른 네임스페이스에 파드를 그릴 권한(ClusterRole)이 주어지지 않았습니다.
- **해결**: ArgoCD는 배포 에이전트 역할을 하므로 광범위한 K8s Admin 권한 또는 특정 타겟 네임스페이스 전용 RoleBinding이 필요합니다. `kubectl create clusterrolebinding` 등으로 권한을 복구합니다.

## 4. App of Apps 패턴 구축 시 꿀팁 방출
운영 환경에서는 수십 개의 Application을 일일이 만들지 않고, 1개의 Application 안에 수십 개의 Application 배포 설정을 끼워 넣는 `App of Apps` 또는 `ApplicationSet` 메커니즘을 씁니다. 만약 루트 앱을 지우면 **하위 앱도 모두 폭파(Cascade Delete)** 될 수 있으므로, 반드시 루트 앱 지우기 전엔 신중하게 백업해두거나 `--cascade=false` 명령어 옵션을 쓰셔야 합니다!
