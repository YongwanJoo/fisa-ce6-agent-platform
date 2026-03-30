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
                f"긴급 상황 발생! 현재 클러스터에서 K8s 장애가 감지되었습니다.\n"
                f"- 에러명: {alert_name}\n"
                f"- 파드명: {pod_name}\n"
                f"- 네임스페이스: {namespace}\n"
                f"- 상세내용: {description}\n\n"
                f"이 장애의 원인을 분석하고 해결책을 찾아 즉시 '디스코드로 보고'해줘!"
            )
            
            try:
                config = {"callbacks": [get_langfuse_handler()]}
            except Exception as e:
                logger.error(f"Langfuse handler initialization failed: {e}")
                config = {}
                
            # 2. 백그라운드에서 LangGraph 에이전트 실행 (Discord Webhook Tool 자동 호출 유도)
            background_tasks.add_task(_graph.invoke, {"question": emergency_prompt}, config)
            
    return {"status": "received"}