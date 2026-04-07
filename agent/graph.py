"""
LangGraph 에이전트 그래프 정의
의도 분류 → 검색 → 신뢰도 평가 → 재검색 or 응답 생성
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
import os
from agent.retriever import retrieve
from agent.llm import classify_intent, generate_answer, rewrite_query

MAX_RETRY = 3
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.75"))

class AgentState(TypedDict):
    question: str
    intent: str
    docs: list
    score: float
    retry_count: int
    answer: str


def classify_node(state: AgentState) -> AgentState:
    # 이미 의도가 설정되어 있다면 (예: 웹훅에서 강제 지정) 분류기를 건너뜁니다.
    if state.get("intent"):
        print(f"⏩ [Graph] 기존 의도 사용: {state['intent']}")
        return {**state, "retry_count": 0}
        
    print(f"🕵️ [Graph] 의도 분류 시작: {state['question'][:50]}...")
    intent = classify_intent(state["question"])
    print(f"🎯 [Graph] 의도 분류 완료: {intent}")
    return {**state, "intent": intent, "retry_count": 0}


def retrieve_node(state: AgentState) -> AgentState:
    print(f"📖 [Graph] 지식베이스 검색 중 (의도: {state['intent']})...")
    try:
        docs = retrieve(state["question"], intent=state["intent"])
        score = max((d.metadata.get("score", 0) for d in docs), default=0)
        print(f"🔍 [Graph] 검색 완료 (결과 {len(docs)}건, 최고 점수 {score:.2f})")
        return {**state, "docs": docs, "score": score}
    except Exception as e:
        print(f"[Fallback] Retrieval error: {e}")
        return {**state, "docs": [], "score": 0.0}


def evaluate_node(state: AgentState) -> Literal["generate", "rewrite", "ask_more"]:
    if state["score"] >= SCORE_THRESHOLD:
        return "generate"
    if state["retry_count"] < MAX_RETRY:
        return "rewrite"
    return "ask_more"


def rewrite_node(state: AgentState) -> AgentState:
    try:
        new_query = rewrite_query(state["question"], state["docs"])
    except Exception:
        new_query = state["question"] 
    return {**state, "question": new_query, "retry_count": state["retry_count"] + 1}


def generate_node(state: AgentState) -> AgentState:
    print(f"✍️ [Graph] 최종 답변 생성 중 (참고문서 {len(state['docs'])}건)...")
    try:
        answer = generate_answer(state["question"], state["docs"])
        print(f"✨ [Graph] 답변 생성 완료")
        return {**state, "answer": answer}
    except Exception as e:
        print(f"❌ [Graph] 답변 생성 실패: {e}")
        return {**state, "answer": f"답변 생성 중 오류가 발생했습니다: {e}"}


def ask_more_node(state: AgentState) -> AgentState:
    answer = (
        "신뢰도가 낮아 정확한 답변을 드리기 어렵습니다. "
        "더 구체적인 오류 로그(Pod 이름, Namespace, 스택 트레이스 등)를 제공해주세요."
    )
    return {**state, "answer": answer}


# --- 신규 라우팅 분기 노드 추가 ---
def direct_answer_node(state: AgentState) -> AgentState:
    answer = (
        "안녕하세요! 저는 Kubernetes 및 ArgoCD 인프라 운영과 장애 해결을 돕는 전문 SRE 에이전트입니다. "
        "인프라와 얽힌 궁금한 점이나 에러 로그를 편하게 던져주세요!"
    )
    return {**state, "answer": answer}


def blocked_node(state: AgentState) -> AgentState:
    answer = (
        "🚫 [Guardrail 작동] 해당 요청은 시스템 보안 정책(Prompt Injection 방지, 비속어 차단)에 의해 블락되었습니다. "
        "기존 지침을 우회하는 내용 없이 인프라 운영 및 트러블슈팅과 관련된 정상적인 질문을 재시도해주세요."
    )
    return {**state, "answer": answer}
# ----------------------------------


def route_intent(state: AgentState) -> str:
    """의도를 바탕으로 실행할 다음 노드를 결정 (Conditional Edge)"""
    intent = state.get("intent", "general")
    if intent == "troubleshoot":
        return "retrieve"
    elif intent == "blocked":
        return "blocked_node"
    else:
        return "direct_answer"


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("classify", classify_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("rewrite", rewrite_node)
    g.add_node("generate", generate_node)
    g.add_node("ask_more", ask_more_node)
    g.add_node("direct_answer", direct_answer_node)
    g.add_node("blocked_node", blocked_node)

    g.set_entry_point("classify")

    # (신규) 의도에 따라 첫 분기 라우팅
    g.add_conditional_edges("classify", route_intent, {
        "retrieve": "retrieve",
        "direct_answer": "direct_answer",
        "blocked_node": "blocked_node"
    })

    g.add_conditional_edges("retrieve", evaluate_node, {
        "generate": "generate",
        "rewrite": "rewrite",
        "ask_more": "ask_more",
    })
    g.add_edge("rewrite", "retrieve")
    
    # 각 응답 생성 노드는 종료
    g.add_edge("generate", END)
    g.add_edge("ask_more", END)
    g.add_edge("direct_answer", END)
    g.add_edge("blocked_node", END)

    return g.compile()
