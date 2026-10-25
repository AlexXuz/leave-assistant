"""Day 5 LangChain 练习：只实现 hits_to_documents 和 build_prepare_chain。"""
from app.paths import PROJECT_ROOT

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda, RunnableSequence

from app.pgvector_service import retrieve_pgvector
from app.course.examples.foundations.policy_qa import build_policy_messages, parse_policy_answer


def hits_to_documents(hits: list[dict]) -> list[Document]:
    """作业 1：把已有检索命中转换为 LangChain Document 列表。

    每项 hit = {"chunk": {...}, "score": 浮点数}。
    Document 的字段：
    - id：chunk["id"]，保留片段 ID，不使用整篇 document_id 替代。
    - page_content：chunk["content"]，保留完整正文。
    - metadata：包含 document_id/title/version/heading，值来自 chunk；
      再加 score，值为 float(hit["score"])。
    保留输入顺序，不修改 hits；空列表返回空列表。不调用检索或模型。
    可用普通 for + append，不要求列表推导式。
    """
    documents = []
    for hit in hits:
        documents.append(Document(
            id=hit["chunk"]["id"],
            page_content=hit["chunk"]["content"],
            metadata={
                "document_id": hit["chunk"]["document_id"],
                "title": hit["chunk"]["title"],
                "version": hit["chunk"]["version"],
                "heading": hit["chunk"]["heading"],
                "score": float(hit["score"])
            }
        ))
    return documents


# noinspection PyTypeChecker
def build_prepare_chain() -> RunnableSequence:
    """作业 2：用 RunnableLambda 和 | 连接下方两个已提供的函数。

    第一步 retrieve_step，第二步 prepare_step。返回组合得到的链对象。
    此函数只组装链，不执行函数；不要在此处写 invoke，也不要给回调加 ()。
    输入：{"question": "问题", "top_k": 2}。
    chain.invoke(输入) 才依次执行两个步骤。
    """
    return RunnableLambda(retrieve_step) | RunnableLambda(prepare_step)


# 以下回调和模型链由助教提供，先阅读，不需要修改。
def retrieve_step(request: dict) -> dict:
    question = request["question"]
    top_k = request.get("top_k", 2)
    hits = retrieve_pgvector(question, top_k)
    return {
        "question": question,
        "top_k": top_k,
        "retrieved_chunks": hits,
        "lc_documents": hits_to_documents(hits),
    }


def prepare_step(state: dict) -> dict:
    documents = [
        {"id": document.id, "content": document.page_content}
        for document in state["lc_documents"]
    ]
    return {
        **state,
        "documents": documents,
        "messages": build_policy_messages(state["question"], documents),
    }


def validate_step(state: dict) -> dict:
    return {
        **state,
        "actual": parse_policy_answer(state["raw_content"], state["documents"]),
    }


def build_answer_chain(model=None) -> RunnableSequence:
    from app.langchain_model import generate_step

    def generate(state):
        return generate_step(state, model=model)

    return RunnableLambda(generate) | RunnableLambda(validate_step)


def build_rag_chain(model=None) -> RunnableSequence:
    """完整链：一次检索 → 构造消息 → 一次模型调用 → 原有业务校验。"""
    return build_prepare_chain() | build_answer_chain(model)
