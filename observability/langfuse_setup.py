"""
Langfuse 관측 설정 — 에이전트 트레이싱 초기화
"""
import os
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

def get_langfuse_handler() -> CallbackHandler:
    """LangChain/LangGraph 콜백에 주입할 Langfuse 핸들러 반환"""
    # Langfuse 3.x의 CallbackHandler는 환경 변수를 알아서 참조합니다.
    return CallbackHandler()

def get_langfuse_client() -> Langfuse:
    """직접 Langfuse API를 호출할 클라이언트 반환"""
    return Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )
