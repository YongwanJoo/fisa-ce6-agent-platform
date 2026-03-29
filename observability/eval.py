"""
에이전트 자동 Eval 스크립트 — GitHub Actions CI에서 실행됨
품질 점수가 PASS_THRESHOLD 미만이면 exit(1)로 배포 차단
"""
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

PASS_THRESHOLD = float(os.getenv("EVAL_PASS_THRESHOLD", "0.75"))
GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "golden_set.json")

# 평가용 테스트 케이스 로드
try:
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        TEST_CASES = json.load(f)
except FileNotFoundError:
    print(f"⚠️ {GOLDEN_SET_PATH} 파일을 찾을 수 없어 기본 케이스를 사용합니다.")
    TEST_CASES = [
        {"question": "Pod가 CrashLoopBackOff 상태입니다.", "expected_keywords": ["crash", "log"]}
    ]


def keyword_score(answer: str, keywords: list[str]) -> float:
    """기대 키워드 중 답변에 포함된 비율을 점수로 반환"""
    answer_lower = answer.lower()
    matched = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return matched / len(keywords)


def run_eval() -> float:
    from agent.graph import build_graph

    graph = build_graph()
    scores = []

    for case in TEST_CASES:
        result = graph.invoke({"question": case["question"]})
        score = keyword_score(result["answer"], case["expected_keywords"])
        scores.append(score)
        print(f"[{'PASS' if score >= PASS_THRESHOLD else 'FAIL'}] score={score:.2f} | {case['question'][:50]}")

    avg = sum(scores) / len(scores)
    print(f"\n총 평균 점수: {avg:.2f} (기준: {PASS_THRESHOLD})")
    return avg


if __name__ == "__main__":
    avg_score = run_eval()
    if avg_score < PASS_THRESHOLD:
        print("❌ Eval 실패 — 배포가 차단됩니다.")
        sys.exit(1)
    print("✅ Eval 통과 — 배포를 진행합니다.")
