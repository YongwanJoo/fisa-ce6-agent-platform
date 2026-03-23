"""
AgentOps — SRE 에이전트 메인 진입점
"""
from dotenv import load_dotenv
load_dotenv()

from agent.graph import build_graph

def main():
    graph = build_graph()
    print("🤖 SRE 에이전트 시작. 종료: Ctrl+C\n")
    while True:
        user_input = input("에러 로그 또는 질문을 입력하세요:\n> ").strip()
        if not user_input:
            continue
        result = graph.invoke({"question": user_input})
        print(f"\n📋 분석 결과:\n{result['answer']}\n")

if __name__ == "__main__":
    main()
