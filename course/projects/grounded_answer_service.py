"""Day3独立任务：错误分层与有依据问答：从提取走向制度。
先读course/tasks/grounded_answer_service.md，接口和错误由你设计；此处尚未接线。
"""
from __future__ import annotations

def prepare_grounded_request(question: str, documents: list[dict]) -> list[dict]:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")

def validate_grounded_answer(answer: dict, documents: list[dict]) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")
