"""
FastAPI 서버 — 에이전트 REST API
"""
from fastapi import FastAPI
from pydantic import BaseModel
from agent.graph import build_graph

app = FastAPI(title="SRE 에이전트 API", version="0.1.0")
_graph = build_graph()


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    intent: str
    retry_count: int


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    result = _graph.invoke({"question": req.question})
    return QueryResponse(
        answer=result["answer"],
        intent=result.get("intent", ""),
        retry_count=result.get("retry_count", 0),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
