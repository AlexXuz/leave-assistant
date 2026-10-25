"""Day5独立任务：pgvector与LangChain：持久检索和编排。
先读course/tasks/persistent_rag_pipeline.md，接口和错误由你设计；此处尚未接线。
"""
from __future__ import annotations

def prepare_indexed_request(question: str, store, top_k: int) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")

def build_pipeline(retrieve, prepare, model, validate) -> object:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")
