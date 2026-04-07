# Terraform 인프라 배포 디버깅 및 State 관리 딥다이브 (AgentOps Knowledge Base)

> **Metadata**
> - **Category**: Infrastructure as Code (IaC)
> - **Keywords**: Terraform, State, Provider, Drift, Lock
> - **Version**: 1.1.0

Terraform은 'Infrastructure as Code(코드로서의 인프라)'의 사실상 업계 표준 솔루션입니다. 하지만 프로덕션 및 CI/CD 환경에서는 로컬 작업과 달리 병렬 충돌(Lock), API 통신 지연(Drift), 모듈 종속성 순서 문제 등으로 인해 예측 불가의 런타임 에러를 동반하곤 합니다.

---

## 1. Remote State Backend 관련 장애 해결

### 1-1. Error: Error acquiring the state lock
- **해결**: `terraform force-unlock <ID>` 명령을 사용하여 고아 락(Orphan Lock)을 제거하십시오. 단, 실제 실행 중인 프로세스가 없는지 반드시 선행 확인해야 합니다.

### 1-2. State Migration (S3 to GCS 등)
- **상세**: 클라우드 벤더를 옮기거나 백엔드 위치를 변경할 때 발생.
- **해결**: 신규 백엔드 블록을 작성한 후 `terraform init -migrate-state` 를 실행하십시오. 기존 상태 데이터가 안전하게 복사됩니다.

---

## 2. Configuration Drift (상태 틀어짐)

### 2-1. 소스코드와 인프라의 불일치
- **원인**: 수동 콘솔 조작으로 인한 상태 이격.
- **해결**: `terraform apply -refresh-only` 를 통해 클라우드 실물 상태를 `.tfstate`에 강제 동기화하거나, 코드를 수정하여 정합성을 맞추십시오.

---

## 3. 리소스 종속성 및 버전 관리

### 3-1. Provider Version Conflicts
- **증상**: `Error: Inconsistent dependency lock file`.
- **원인**: 협업 시 각자의 로컬 환경에서 다른 버전의 Provider를 사용하여 `.terraform.lock.hcl`이 충돌함.
- **해결**: `terraform init -upgrade` 를 통해 모든 팀원이 동일한 버전의 Provider를 사용하도록 고정하십시오.

### 3-2. Sensitive Data Leak (민감 데이터 노출)
- **주의**: 테라폼 상태 파일(`.tfstate`)에는 DB 비밀번호 등이 **평문**으로 저장됩니다.
- **방어**: 백엔드 버킷(S3/GCS)에 대해 엄격한 ACL을 설정하고, 반드시 클라우드 KMS를 통한 암호화를 활성화하십시오.

---

## 4. AgentOps 운영 팁 (SRE 에이전트 활용)
- **Plan 결과 분석**: 에이전트에게 `terraform plan` 결과를 전달하여, 어떤 리소스가 삭제(Destroy)될 위험이 있는지 미리 보고받으십시오.
- **Drift 탐지**: 정기적으로 에이전트가 `plan`을 실행하게 하여, 의도치 않은 인프라 변경 사항이 있는지 감시하도록 하십시오.
