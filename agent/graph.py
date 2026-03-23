"""
LangGraph 에이전트 그래프 정의
의도 분류 → 검색 → 신뢰도 평가 → 재검색 or 응답 생성
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from agent.retriever import retrieve
from agent.llm import classify_intent, generate_answer, rewrite_query

MAX_RETRY = 3
SCORE_THRESHOLD = 0.75


class AgentState(TypedDict):
    question: str
    intent: Literal["troubleshoot"]
    docs: list
    score: float
    retry_count: int
    answer: str


def classify_node(state: AgentState) -> AgentState:
    intent = classify_intent(state["question"])
    return {**state, "intent": intent, "retry_count": 0}


def retrieve_node(state: AgentState) -> AgentState:
    docs = retrieve(state["question"], intent=state["intent"])
    score = max((d.metadata.get("score", 0) for d in docs), default=0)
    return {**state, "docs": docs, "score": score}


def evaluate_node(state: AgentState) -> Literal["generate", "rewrite", "ask_more"]:
    if state["score"] >= SCORE_THRESHOLD:
        return "generate"
    if state["retry_count"] < MAX_RETRY:
        return "rewrite"
    return "ask_more"


def rewrite_node(state: AgentState) -> AgentState:
    new_query = rewrite_query(state["question"], state["docs"])
    return {**state, "question": new_query, "retry_count": state["retry_count"] + 1}


def generate_node(state: AgentState) -> AgentState:
    answer = generate_answer(state["question"], state["docs"])
    return {**state, "answer": answer}


def ask_more_node(state: AgentState) -> AgentState:
    answer = (
        "신뢰도가 낮아 정확한 답변을 드리기 어렵습니다. "
        "더 구체적인 오류 로그(Pod 이름, Namespace, 스택 트레이스 등)를 제공해주세요."
    )
    return {**state, "answer": answer}


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("classify", classify_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("rewrite", rewrite_node)
    g.add_node("generate", generate_node)
    g.add_node("ask_more", ask_more_node)

    g.set_entry_point("classify")
    g.add_edge("classify", "retrieve")
    g.add_conditional_edges("retrieve", evaluate_node, {
        "generate": "generate",
        "rewrite": "rewrite",
        "ask_more": "ask_more",
    })
    g.add_edge("rewrite", "retrieve")
    g.add_edge("generate", END)
    g.add_edge("ask_more", END)

    return g.compile()
