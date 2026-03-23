"""
LLM 호출 — 의도 분류 / 쿼리 재작성 / 답변 생성
"""
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

_llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)


def classify_intent(question: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 SRE 에이전트의 의도 분류기입니다.\n"
            "입력이 Kubernetes/ArgoCD/Terraform 에러 트러블슈팅이면 'troubleshoot'을 반환하세요.\n"
            "반드시 'troubleshoot'만 반환합니다."
        )),
        ("human", "{question}"),
    ])
    result = (prompt | _llm).invoke({"question": question})
    return "troubleshoot"


def rewrite_query(question: str, docs: list) -> str:
    context = "\n".join(d.page_content[:200] for d in docs[:3])
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "검색 결과가 충분하지 않습니다. 아래 문서 조각을 참고해 "
            "더 구체적인 검색 쿼리로 재작성하세요. 쿼리만 반환합니다."
        )),
        ("human", "원본 질문: {question}\n\n검색 결과 일부:\n{context}"),
    ])
    result = (prompt | _llm).invoke({"question": question, "context": context})
    return result.content.strip()


def generate_answer(question: str, docs: list) -> str:
    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('collection', '')}] {d.page_content}" for d in docs[:5]
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 Kubernetes/ArgoCD 전문 SRE 에이전트입니다.\n"
            "아래 문서를 기반으로 에러 원인과 해결 방법을 한국어로 설명하세요.\n"
            "문서에 없는 내용은 추측하지 말고 '문서에서 확인되지 않음'으로 표시하세요."
        )),
        ("human", "질문: {question}\n\n참고 문서:\n{context}"),
    ])
    result = (prompt | _llm).invoke({"question": question, "context": context})
    return result.content.strip()
