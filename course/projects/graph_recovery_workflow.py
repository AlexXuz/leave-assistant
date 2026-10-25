"""独立接线：可暂停、重建并恢复的申请图。

先读 course/tasks/graph_recovery_workflow.md。独立设计接线，复用已验收业务接口，禁止替换为作者示范调用。
完成后提交自己的正常/变体/失败与恢复证据；热身函数通过不代表本任务完成。
"""
from __future__ import annotations
from course.projects.contracts import WorkflowServices

def build_graph(services: WorkflowServices, checkpointer) -> object:
    """输入输出与服务端口见任务书；实现与接口细节由学习者设计。"""
    raise NotImplementedError("独立任务尚未实现")

def run_action(graph, thread_id: str, action: str, revision: int | None = None) -> dict:
    """输入输出与服务端口见任务书；实现与接口细节由学习者设计。"""
    raise NotImplementedError("独立任务尚未实现")
