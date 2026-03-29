"""
에이전트 자동 Eval 스크립트 — GitHub Actions CI에서 실행됨
품질 점수가 PASS_THRESHOLD 미만이면 exit(1)로 배포 차단
"""
import json
import os
import sys
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

PASS_THRESHOLD = float(os.getenv("EVAL_PASS_THRESHOLD", "0.75"))
GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "golden_set.json")

try:
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        TEST_CASES = json.load(f)
except FileNotFoundError:
    print(f"⚠️ {GOLDEN_SET_PATH} 파일을 찾을 수 없어 기본 케이스를 사용합니다.")
    TEST_CASES = [
        {"question": "Pod가 CrashLoopBackOff 상태입니다.", "expected_keywords": ["crash", "log"]}
    ]


class LLMJudgeResult(BaseModel):
    score: float = Field(description="0.0에서 1.0 사이의 평가 점수")
    reason: str = Field(description="해당 점수를 부여한 상세하고 명확한 1문장 사유")

def llm_judge_score(question: str, answer: str, ground_truth: str) -> tuple[float, str]:
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 사내 SRE 에이전트의 답변 품질을 엄격하게 평가하는 심사위원(LLM-as-a-Judge)입니다.\n"
            "사용자의 질문에 대해 에이전트가 생성한 답변이 'Ground Truth(모범 답안)'와 의미상 얼마나 일치하고 정확한지 평가하세요.\n"
            "단순 키워드가 다르더라도 의미와 의도가 같다면 부분/만점 처리를 해야 합니다.\n"
            "[평가 기준]\n"
            "- 1.0: 핵심 원인 분석과 해결책(명령어 포함)이 모범 답안과 정확히 의미상 일치함\n"
            "- 0.5: 일부 내용만 맞거나, 중요한 설명/핵심 명령어 등이 부분적으로 누락되어 해결에 부족함\n"
            "- 0.0: 완전히 틀렸거나, 질문과 무관하거나, 모범 답안의 해결책을 단 하나도 제시하지 못함\n"
        )),
        ("human", "질문: {question}\n\n모범 답안: {ground_truth}\n\n에이전트 답변: {answer}"),
    ])
    
    evaluator = prompt | llm.with_structured_output(LLMJudgeResult)
    result = evaluator.invoke({"question": question, "ground_truth": ground_truth, "answer": answer})
    return result.score, result.reason

def keyword_score(answer: str, keywords: list[str]) -> float:
    """하위 호환성을 위한 구버전 키워드 점수 계산 (ground_truth가 없는 예전 데이터용)"""
    if not keywords:
        return 0.0
    answer_lower = answer.lower()
    matched = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return matched / len(keywords)


def run_eval() -> float:
    from agent.graph import build_graph
    from observability.langfuse_setup import get_langfuse_handler

    graph = build_graph()
    scores = []
    
    try:
        handler = get_langfuse_handler()
        config = {"callbacks": [handler]}
    except Exception as e:
        print(f"⚠️ Langfuse 연동 실패 (평가만 진행합니다): {e}")
        handler = None
        config = {}

    for case in TEST_CASES:
        result = graph.invoke(
            {"question": case["question"], "retry_count": 0, "docs": [], "score": 0.0}, 
            config=config
        )
        
        ground_truth = case.get("ground_truth", "")
        if ground_truth:
            score, reason = llm_judge_score(case["question"], result["answer"], ground_truth)
        else:
            score = keyword_score(result["answer"], case["expected_keywords"])
            reason = "모범 답안 정보가 없어 키워드 기반으로 평가됨"
            
        scores.append(score)
        
        status = 'PASS' if score >= PASS_THRESHOLD else 'FAIL'
        intent = result.get("intent", "unknown")
        print(f"[{status}] score={score:.2f} | 의도: {intent} | Q: {case['question'][:50]}...")
        
        print(f"   ↳ 💡 LLM 평가 사유: {reason}")
        short_ans = result['answer'].replace('\n', ' ')
        print(f"   ↳ 🤖 에이전트 답변: {short_ans[:200]}...\n")

    if not scores:
        print("⚠️ 평가할 테스트 케이스가 없습니다.")
        return 0.0

    avg = sum(scores) / len(scores)
    print(f"\n최종 LLM-as-a-Judge 평균 점수: {avg:.2f} (기준: {PASS_THRESHOLD})")
    
    if handler:
        if hasattr(handler, "langfuse"):
            handler.langfuse.flush()
        elif hasattr(handler, "auth"):
            handler.auth.flush()
        
    return avg


if __name__ == "__main__":
    avg_score = run_eval()
    if avg_score < PASS_THRESHOLD:
        print("❌ Eval 실패 — 배포가 차단됩니다.")
        sys.exit(1)
    print("✅ Eval 통과 — 배포를 진행합니다.")
