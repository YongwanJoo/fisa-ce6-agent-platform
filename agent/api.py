"""
FastAPI 서버 — 에이전트 REST API
"""
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
from agent.graph import build_graph
from observability.langfuse_setup import get_langfuse_handler
import logging

app = FastAPI(title="SRE 에이전트 API", version="0.1.0")
_graph = build_graph()
logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    intent: str
    retry_count: int

@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    try:
        config = {"callbacks": [get_langfuse_handler()]}
    except Exception as e:
        logger.error(f"Langfuse handler initialization failed: {e}")
        config = {}

    result = _graph.invoke({"question": req.question}, config=config)
    return QueryResponse(
        answer=result["answer"],
        intent=result.get("intent", ""),
        retry_count=result.get("retry_count", 0),
    )

@app.get("/health")
async def health():
    return {"status": "ok"}

# --- AlertManager 자동 신고 접수 엔드포인트 ---
@app.post("/webhook/alertmanager")
async def alertmanager_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    
    for alert in payload.get("alerts", []):
        if alert.get("status") == "firing":
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            
            pod_name = labels.get("pod", "Unknown Pod")
            namespace = labels.get("namespace", "Unknown Namespace")
            alert_name = labels.get("alertname", "Unknown Alert")
            description = annotations.get("description", "상세 내용 없음")
            
            # 1. 강제 기상 프롬프트 조합
            emergency_prompt = (
                f"🚨 [긴급 장애 분석 요청] 아래의 K8s 장애가 감지되었습니다. 지식 베이스를 철저히 검색하여 이 장애의 근본 원인을 분석하고, 전문가 수준의 조치 명령어(kubectl 등)가 포함된 **장애 보고서**를 작성하여 즉시 `send_discord_alert`로 보고하세요!\n\n"
                f"--- 장애 상세 ---\n"
                f"- 에러명: {alert_name}\n"
                f"- 파드명: {pod_name}\n"
                f"- 네임스페이스: {namespace}\n"
                f"- 상세내용: {description}"
            )
            
            try:
                config = {"callbacks": [get_langfuse_handler()]}
            except Exception as e:
                logger.error(f"Langfuse handler initialization failed: {e}")
                config = {}
                
            # 2. 백그라운드 분석 실행 함수 정의 및 등록
            def run_analysis(prompt, config):
                try:
                    print(f"🔍 [Background Task] 분석 시작: {prompt[:100]}...")
                    res = _graph.invoke({"question": prompt}, config=config)
                    print(f"✅ [Background Task] 분석 완료 후 응답: {res.get('answer', '응답 없음')[:100]}...")
                except Exception as ex:
                    print(f"❌ [Background Task] 분석 중 치명적 오류 발생: {ex}")

            background_tasks.add_task(run_analysis, emergency_prompt, config)
            print(f"📡 [Webhook] AlertManager 알람 수신 및 분석 작업 등록 완료 (에러명: {alert_name})")
            
    return {"status": "received"}