terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# GKE 클러스터 껍데기 (Control Plane)
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.zone

  # 노드 풀(Node Pool)을 분리하여 관리하기 위해 기본 노드 삭제
  remove_default_node_pool = true
  initial_node_count       = 1

  # 네트워크 설정 및 VPC Native 모드 활성화
  networking_mode = "VPC_NATIVE"
  ip_allocation_policy {}

  deletion_protection = false # 쉽게 삭제할 수 있도록 설정 (PoC 용도)
}

# 실제 Pod들이 띄워질 Worker Node Pool
resource "google_container_node_pool" "primary_nodes" {
  name       = "${var.cluster_name}-node-pool"
  location   = var.zone
  cluster    = google_container_cluster.primary.name
  node_count = 2 # e2-standard-2 노드 2개 생성 (충분한 리소스)

  node_config {
    machine_type = "e2-standard-2" # 2 vCPU, 8GB RAM (비용/효율 최적화)
    disk_size_gb = 50              # 디스크 50GB
    disk_type    = "pd-standard"

    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    
    labels = {
      role     = "agentops"
      env      = "dev"
    }
  }
}
