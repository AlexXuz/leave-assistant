"""独立接线：跨轮修改、压缩和偏好删除。

先读 course/tasks/conversation_context_pipeline.md。独立设计接线，复用已验收业务接口，禁止替换为作者示范调用。
完成后提交自己的正常/变体/失败与恢复证据；热身函数通过不代表本任务完成。
"""
from __future__ import annotations
from course.projects.contracts import ContextServices

def prepare_request(question: str, turns: list[dict], services: ContextServices, budget_chars: int) -> dict:
    """输入输出与服务端口见任务书；实现与接口细节由学习者设计。"""
    raise NotImplementedError("独立任务尚未实现")

def delete_preference(services: ContextServices) -> dict:
    """输入输出与服务端口见任务书；实现与接口细节由学习者设计。"""
    raise NotImplementedError("独立任务尚未实现")
