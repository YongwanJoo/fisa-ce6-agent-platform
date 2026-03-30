# Terraform 인프라 배포 디버깅 및 State 관리 딥다이브 (SRE 세미나용)

Terraform은 'Infrastructure as Code(코드로서의 인프라)'의 사실상 업계 표준 솔루션입니다. 하지만 프로덕션 및 CI/CD 환경에서는 로컬 작업과 달리 병렬 충돌(Lock), API 통신 지연(Drift), 모듈 종속성 순서 문제 등으로 인해 예측 불가의 런타임 에러를 동반하곤 합니다.

## 1. Remote State Backend 관련 장애 해결

### 1-1. Error: Error acquiring the state lock
가장 빈번하게 발생하며, 가장 다루기 까다로운 락타임(Locktime) 에러입니다.
- **주요 원인(Root Cause)**:
  여러 SRE 엔지니어가 동일한 작업 공간에서 서로 AWS나 GCP 인프라를 만들려고 `terraform apply`를 병렬로 쳤기 때문에 일관성 붕괴를 막기 위해 테라폼이 락을 겁니다. 
  때때로 클라우드 백엔드 저장소(AWS S3+DynamoDB 또는 GCS) 통신 단절, CI/CD 파이프라인의 강제 킬(Kill) 등의 이유로 "인프라는 만들어지지도 않았는데 락만 영원히 남는 이른바 '고아 락(Orphan Lock)'"이 생성되기도 합니다.
- **해결 방안(Troubleshooting)**:
  우선 파이프라인이나 누군가의 로컬에서 진짜로 돌고 있는 프로세스가 없는지 팀 메신저로 최종 체크합니다.
  그 뒤에 아래 명령 실행으로 GCS 버킷 및 AWS DynamoDB에 잡혀있는 락 세션을 강제로 쪼개버립니다.
  `terraform force-unlock <ID-FROM-ERROR-MESSAGE>`

### 1-2. Backend Initialization 실패 (Backend Block 오류)
- **주요 원인**: Terraform 바이너리 버전이 백엔드 모듈이 요구하는 버전과 일치하지 않거나 클라우드 스토리지 버킷의 이름이 오타로 들어갔습니다.
- **해결 방안**: `.terraform/` 숨김 디렉토리를 통째로 삭제(캐시 제거)한 뒤에, 버전을 명확히 맞추고 `terraform init -reconfigure` 를 실행해 백엔드 세팅을 강제로 재초기화합니다.

## 2. Configuration Drift (결함/상태 틀어짐 현상)

### 2-1. 소스코드와 인프라의 다름 (Drift Detected)
테라폼의 `apply`가 다 끝났는데 한참 뒤 구글 클라우드 콘솔 화면을 보고 답답해진 인프라 팀원이 마우스 클릭으로 DB의 용량을 50기가에서 100기가로 몰래 늘렸을 때 터집니다.
- **주요 원인**: 테라폼 상태 파일(`.tfstate`)에는 DB 용량이 여전히 50GB로 박혀있는데, 리얼타임 API 인프라는 100GB이므로 다음 `terraform plan` 때 전부 에러나거나 의도치 않은 하향 옵션(Downgrade)을 강제하려고 합니다.
- **해결 방안(Troubleshooting)**:
  상황에 따라 두 가지 대응이 필요합니다.
  1) 수동 세팅이 맞고 코드가 틀렸다면: 소스코드의 DB 선언 부분을 100GB로 올린 다음 커밋합니다.
  2) 실제 클라우드 상태를 `.tfstate`가 다시 똑똑하게 인공 스캔하게 만듭니다. `terraform apply -refresh-only` 명령을 쳐서 GCS에 있는 상태값을 클라우드 현실과 100% 동기화시켜 줍니다.

## 3. 리소스 종속성 타임아웃 및 권한 에러

### 3-1. Permission Denied (403 Forbidden Error)
- **주요 원인**: `terraform plan`은 인프라를 그리는 작업이라 권한이 덜 필요하지만, 실제 `apply`로 서버나 DB를 생성을 시도할 때 Google Cloud/AWS API에서 "너 해당 서비스 계정(Account)에 리소스 생성 IAM 롤 없음" 이라고 에러를 뱉습니다.
- **해결 방안**: `.tf` 파일 안에 기술된 Cloud Provider 세팅 구문 내 `credentials / service_account` 정보가 제대로 들어갔는지 검증하시고, 클라우드 어드민 센터에서 GKE Cluster Admin 이나 Instance Admin 같은 필요한 롤(Role)을 즉시 부여해야 통과됩니다.

### 3-2. Timeout Waiting for Resource Creation
수십 분 동안 파이프라인에서 뺑뺑 돌다가 "Timeout" 에러가 터지고 멈춥니다.
- **주요 원인**: Managed Kubernetes (EKS, GKE) 클러스터 혹은 대형 Cloud SQL 등은 초기 부트스트랩을 하는 데 기본 15분 이상이 지연됩니다. 그런데 Terraform이 해당 리소스를 기다려주는 인내심 제한선(Timeouts 설정을 따로 안 했을 경우 기본값) 보다 더 딜레이 되면 발생.
- **해결 방안**:
  리소스 블록 내에 `timeouts` 하위 블록을 명시하여 타임아웃 데드라인을 자비롭게 45분 정도로 길게 잡아줍니다.
  ```hcl
  resource "google_container_cluster" "primary" {
    # 생략...
    timeouts {
      create = "45m"
      update = "45m"
    }
  }
  ```

### 3-3. 무시무시한 리소스의 철거 방지 에러
프로덕션용 K8s 클러스터나 DB는 정말 누군가 실수로 테라폼 코드에서 삭제하거나 마우스를 잘못 눌러도 `apply`가 되면 안됩니다.
그래서 테라폼 소스코드 `lifecycle { prevent_destroy = true }` 라고 걸려있는 코드를 지우려 하면 치명적 에러가 뜹니다.
- **해결**: 정말 삭제를 원하신다면 먼저 코드로 들어가 저 `prevent_destroy` 값을 `false` 로 바꿔서 `apply`로 저장하고, 그 다음에 리소스를 철거(`terraform destroy`) 하시면 됩니다.
