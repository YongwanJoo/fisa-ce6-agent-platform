"""
AgentOps — SRE 에이전트 메인 진입점
"""
from dotenv import load_dotenv
load_dotenv()

from agent.graph import build_graph
from observability.langfuse_setup import get_langfuse_handler

def main():
    graph = build_graph()
    try:
        langfuse_handler = get_langfuse_handler()
        if hasattr(langfuse_handler, 'auth_check'):
            langfuse_handler.auth_check()
        config = {"callbacks": [langfuse_handler]}
    except Exception as e:
        print(f"⚠️ Langfuse 연동 알림: 트레이싱이 비활성화 되었습니다 ({e})")
        config = {}

    print("🤖 SRE 에이전트 시작. 종료: Ctrl+C")
    while True:
        try:
            user_input = input("\n에러 로그 또는 질문을 입력하세요:\n> ").strip()
            if not user_input:
                continue
            result = graph.invoke({"question": user_input}, config=config)
            print(f"\n📋 분석 결과:\n{result['answer']}")
            
            if "callbacks" in config:
                if hasattr(langfuse_handler, "flush"):
                    langfuse_handler.flush()
                # Langfuse 3.x 의 경우 get_langfuse().flush() 를 사용
                elif hasattr(langfuse_handler, "get_langfuse"):
                    langfuse_handler.get_langfuse().flush()
                
        except KeyboardInterrupt:
            print("\n에이전트를 종료합니다. 👋")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()
