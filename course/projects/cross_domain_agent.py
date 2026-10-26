"""Day24 learner-owned Agent transfer and durable execution scaffold.

Read course/tasks/cross_domain_agent_delivery.md. Define a new domain's DTOs,
state, tools, success criteria, persistence and host-bound service adapters.
These function names are starting points, not a complete application design.
"""
from __future__ import annotations

from typing import Any


async def start_task(request: dict[str, Any], services: Any) -> dict[str, Any]:
    """Validate the new-domain task and start its durable execution.

    services must bind trusted identity; model/request text cannot grant scope.
    Return your documented task id, revision, status and result/evidence view.
    Persist enough state to continue after a real worker restart.
    """
    raise NotImplementedError("跨领域任务设计与启动由学习者实现")


async def resume_task(
    task_id: str, decision: dict[str, Any], services: Any
) -> dict[str, Any]:
    """Resume a task after verifying ownership, revision and explicit decision.

    Design worker concurrency and stable external-action idempotency. Reconcile
    remote facts when an action succeeded before its observation was persisted;
    an uncertain result must not silently trigger an unrelated new action.
    """
    raise NotImplementedError("实现人工决策、崩溃恢复与副作用核对")


async def read_task(task_id: str, services: Any) -> dict[str, Any]:
    """Return an authorized state/evidence view without expanding user scope."""
    raise NotImplementedError("实现可信身份下的任务状态读取")
