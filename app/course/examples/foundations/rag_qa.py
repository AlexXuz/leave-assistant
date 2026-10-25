"""RAG 请求组装：Day 5 将文件检索切换为数据库检索，保留后续消息结构。"""
from app.paths import PROJECT_ROOT

import json
from pathlib import Path

from app.embeddings import embed_documents, embed_query
from app.course.examples.foundations.policy_qa import build_policy_messages
from app.pgvector_service import retrieve_pgvector
from app.course.examples.foundations.retrieval import rank_chunks
from app.vector_index import load_index

RAG_PROMPT_VERSION = "policy-rag-v1"
CHUNKS_PATH = PROJECT_ROOT / "data" / "policy_chunks.json"


def prepare_rag_request(question: str, top_k: int = 2) -> dict:
    """Day 5 第一项：仅替换函数开头的文件检索部分。

    当前开头是 load_index → embed_query → rank_chunks 三步。
    改为调用已导入的 retrieve_pgvector(question, top_k)，接收命中列表。
    该入口管理数据库连接和只读事务，内部复用你昨天的 search_pgvector。
    问题只在该入口中编码一次；本函数不再调用 load_index/embed_query/rank_chunks。

    保留后面的 documents、build_policy_messages 和三个键的返回结构。
    不重写 Prompt、不改片段 ID、不调用聊天模型、不自动重新入库。
    数据库不可用或集合过期时让异常传出，不静默回退到文件索引。

    Day 4 文件基线已由助教保存在 app/file_rag_baseline.py。
    作业前运行 scripts.check_pgvector_rag 显示 FAIL 属于预期。
    """
    top_k_chunks = retrieve_pgvector(question, top_k)
    documents = []
    for top_k_chunk in top_k_chunks:
        chunk = top_k_chunk["chunk"]
        documents.append({
            "id": chunk["id"],
            "content": chunk["content"]
        })
    messages = build_policy_messages(question, documents)
    result = {
        "retrieved_chunks": top_k_chunks,
        "documents": documents,
        "messages": messages
    }
    return result


# 以下读取由助教提供。
def load_chunks() -> list[dict[str, str]]:
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("片段文件应为非空列表，请先运行 scripts.check_policy_chunks --write")
    return chunks
