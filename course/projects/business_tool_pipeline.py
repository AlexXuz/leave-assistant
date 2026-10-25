"""Day10独立任务：Tool Calling：让模型查询真实业务事实。
先读course/tasks/business_tool_pipeline.md，接口和错误由你设计；此处尚未接线。
"""
from __future__ import annotations

def dispatch_tool(name: str, arguments: dict, trusted_identity, services) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")

def respond_with_tools(question: str, model, services) -> dict:
    """按任务书实现自己的链路，不调用完整示范冒充独立完成。"""
    raise NotImplementedError("独立任务尚未实现")
