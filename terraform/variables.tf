variable "project_id" {
  description = "GCP 프로젝트 ID"
  type        = string
}

variable "region" {
  description = "GCP 리전"
  type        = string
  default     = "asia-northeast3" # 서울 리전
}

variable "zone" {
  description = "GCP 존"
  type        = string
  default     = "asia-northeast3-a"
}

variable "cluster_name" {
  description = "생성할 GKE 클러스터 이름"
  type        = string
  default     = "sre-agent-cluster"
}
