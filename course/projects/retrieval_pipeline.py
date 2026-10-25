"""Day4独立任务：最小RAG：切分、向量、排序与请求组装。
先读course/tasks/retrieval_pipeline.md，接口和错误由你设计；此处尚未接线。
"""
from __future__ import annotations

def prepare_corpus(documents: list[dict], embedder) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")

def retrieve_context(question: str, corpus: dict, embedder, top_k: int) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")
