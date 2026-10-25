"""Day 4 已验收文件路径的基线；助教保留，供索引回归和后续对照。"""

from app.embeddings import embed_query
from app.course.examples.foundations.policy_qa import build_policy_messages
from app.course.examples.foundations.retrieval import rank_chunks
from app.vector_index import load_index


def prepare_rag_request(question: str, top_k: int = 2) -> dict:
    chunks, chunk_vectors, manifest = load_index()
    query_vector = embed_query(question)
    hits = rank_chunks(query_vector, chunk_vectors, chunks, top_k)
    documents = []
    for hit in hits:
        chunk = hit["chunk"]
        documents.append({"id": chunk["id"], "content": chunk["content"]})
    return {
        "retrieved_chunks": hits,
        "documents": documents,
        "messages": build_policy_messages(question, documents),
    }
