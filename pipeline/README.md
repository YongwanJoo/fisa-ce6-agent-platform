# pipeline/

이 디렉토리는 GKE(클러스터 인프라) 환경에 격리 배포된 **자동화 파이프라인(n8n)** 관리를 위한 영역입니다.

---

## 💡 왜 n8n을 GCP K8s 환경에 올렸나요?

단일 머신(로컬 노트북)에서 동작할 땐 내가 노트북을 끄면 문서 크롤링이 멈춥니다.
GCP K8s(sre-agent 네임스페이스) 내부에 n8n을 띄우면:
1. **서버리스 완전 자동화**: 매일 새벽 3시에 공식 문서 URL을 스캔하여 K8s에 떠있는 Qdrant에 꽂아 넣습니다.
2. **보안/속도 극대화**: 에이전트, Qdrant, n8n 세 가지 파드가 동일한 망 안에 있어 `http://qdrant-svc:6333` 이라는 내부 주소로 빛보다 빠르게 통신합니다. 외부 트래픽 해킹 위험도 0입니다.

---

## n8n 클라우드 접근 방법 가이드

n8n 데이터는 GKE 영구 디스크(5GB)에 안전하게 쌓이고 있습니다. 외부에서 화면을 보고 설정할 땐 K8s 포트포워딩을 이용합니다.

### 1단계: K8s에서 포널 열기
(터미널 창을 하나 켜두고 명령어를 입력해두면 됩니다)
```bash
kubectl port-forward svc/n8n-svc 5678:5678 -n sre-agent
```

### 2단계: 웹 접속 및 계정 생성
- 브라우저에서 `http://localhost:5678` 로 접속합니다.
- (최초 1회만) 컨테이너가 처음 구동되었으므로 관리자 계정과 비밀번호를 새로 설정합니다.

### 3단계: 워크플로우 설정 및 복원
1. 우상단 **메뉴 → Import from File** 클릭.
2. 로컬 디렉토리의 `.json` 내보내기 파일 선택.
3. 워크플로우가 로드되면 **Qdrant Credential** 설정 창에 K8s 내부 주소를 입력합니다:
   - URL: `http://qdrant-svc:6333`  (GKE 클러스터 내부 DNS 매핑 마법입니다) 
4. **Activate (활성화) 토글 켜기!**

---

## 📦 동기화 파이프라인 목록

> 현재 JSON 파일은 n8n에서 워크플로우를 테스트 완성한 후 Export해서 이 디렉토리에 백업해 둡니다.

| 백업 파일명 | 목적 | 트리거 기준 |
|--------|------|--------|
| `k8s_docs_ingest.json` | K8s/ArgoCD 공식 문서 다운로드 후 `k8s_docs` 적재 | 매일 00:00 자동 수집 |
| `resolved_cases_ingest.json` | 사내 Wiki 등 문제 해결 사례 API 크롤링 → `resolved_cases` 적재 | 매일 03:00 정기 점검 |

---

## Troubleshooting

- **워크플로우가 안 돌아가요**: n8n 포드 로그를 확인해야 합니다. `kubectl logs -n sre-agent deploy/n8n`
- **Qdrant Connection Error**: Qdrant 주소를 로컬호스트가 아닌 K8s 내부 주소 `http://qdrant-svc:6333`로 변경했는지 꼭 다시 확인해주세요!
