# ArgoCD 심층 동기화 및 장애 대응 매뉴얼 (AgentOps Knowledge Base)

> **Metadata**
> - **Category**: Continuous Delivery / GitOps
> - **Keywords**: ArgoCD, Sync, Health, ApplicationSet, Rollback
> - **Version**: 1.1.0

ArgoCD는 GitOps의 원칙을 단일 진실의 근원(Single Source of Truth)으로 구현하는 강력한 쿠버네티스 CD 도구이지만, 그 구조가 선언적이므로 배포 시 다양한 상태 오류(Sync, Health 문제)가 발생할 수 있습니다. 

---

## 1. Application 동기화(Sync) 상태의 불일치

### 1-1. OutOfSync (동기화 벗어남) 현상
Git 저장소의 YAML 내용과 쿠버네티스 클러스터의 실제 상태가 어긋났을 때 나타나는 가장 대표적인 노란색 경고입니다.
- **주요 원인(Root Cause)**:
  1. 수동 조작: `kubectl apply`를 통한 수동 변경.
  2. Mutating Webhooks: Istio, Linkerd 등 사이드카 인젝터가 배포 직후 필드를 변경.
  3. HPA 연동 이슈: Git에는 `replicas: 1`인데 HPA가 숫자를 바꾼 경우.
- **해결 방안**:
  `ignoreDifferences` 설정을 통해 시스템이 자동으로 변경해야 하는 필드(예: replicas, 특정 어노테이션)를 ArgoCD 감시 대상에서 제외하십시오.

### 1-2. Infinite Sync Loop (무한 동기화 루프)
- **증상**: ArgoCD가 `Syncing`과 `Synced`를 무한히 반복하며 파드를 계속 재시작하는 현상.
- **원인**: 배포된 리소스 자체가 스스로 필드를 업데이트하고(예: Status 업데이트), ArgoCD는 이를 "Git과 다르다"고 판단해 다시 덮어쓰는 과정이 반복됨.
- **해결**: `SyncOptions=Prune=false` 옵션을 확인하거나, 해당 필드를 `ignoreDifferences`에 추가하여 루프를 끊어야 합니다.

---

## 2. Health 확인 불가 및 Degraded 에러

### 2-1. Degraded (저하됨 / 레드 알람)
- **점검**: ArgoCD 트리에서 붉은색 깨진 하트 노드를 클릭하여 `Logs` 및 `Events`를 확인하십시오. 대부분 K8s 파드의 `CrashLoopBackOff`나 `OOMKilled` 문제로 귀결됩니다.

### 2-2. Automated Rollback 전략
- **팁**: 장애 발생 시 즉시 이전 상태로 돌아가려면 `syncPolicy`에 `automated: { prune: true, selfHeal: true }`를 설정하십시오. 하지만 데이터 파손 위험이 있는 DB 마이그레이션 등에서는 수동 롤백을 권장합니다.

---

## 3. 권한 및 보안 관련 에러 (RBAC Issues)

### 3-1. Permission Forbidden
- **원인**: ArgoCD ServiceAccount가 타겟 네임스페이스에 대한 `ClusterRole` 권한이 없음.
- **해결**: ArgoCD가 설치된 네임스페이스의 권한 설정을 확인하고 필요시 `ClusterRoleBinding`을 갱신하십시오.

---

## 4. AgentOps 운영 팁 (SRE 에이전트 활용)
- **Sync History 분석**: 에이전트에게 최근의 `Sync History`를 분석하게 하여, 특정 커밋 이후 장애가 발생했는지 판단하도록 하십시오.
- **Diff 기반 조언**: 에이전트에게 `ArgoCD Diff` 결과를 전달하여, 어떤 인프라 설정 변경이 현재의 장애를 유발했을 가능성이 높은지 추론하도록 시키십시오.

