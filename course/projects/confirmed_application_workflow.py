"""Day11独立任务：业务工作流：预检、明确确认与幂等提交。
先读course/tasks/confirmed_application_workflow.md，接口和错误由你设计；此处尚未接线。
"""
from __future__ import annotations

def prepare_application(text: str, services) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")

def confirm_application(draft_id: str, revision: int, services) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")

def submit_application(draft_id: str, revision: int, key: str, services) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")
