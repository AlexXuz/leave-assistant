"""Day1独立任务：Python与模型调用：从消息到结构化结果。
先读course/tasks/model_request_pipeline.md，接口和错误由你设计；此处尚未接线。
"""
from __future__ import annotations

def prepare_messages(text: str, reference_time: str) -> list[dict]:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")

def request_completion(messages: list[dict], client) -> str:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")

def parse_payload(content: str) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")
