"""Day19 learner-owned customer-support Agent. No implementation is supplied.

Read course/tasks/single_agent_delivery.md first. The evaluator calls
``evaluate_case(case, tools)`` and independently captures tool observations.
The public suite is for practice; do not read expected/fixture fields to answer.
"""
from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict


class Usage(TypedDict):
    prompt_tokens: int | None
    completion_tokens: int | None


class AgentResult(TypedDict):
    status: Literal["completed", "needs_input", "blocked", "failed"]
    answer: str
    evidence_ids: list[str]
    model_calls: int
    usage: Usage


class ToolPort(Protocol):
    """Host-owned identity; a teaching API, not arbitrary-code isolation."""

    @property
    def schemas(self) -> list[dict[str, Any]]: ...

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


async def run_case(
    case: dict[str, Any], tools: ToolPort, *, model: Any
) -> AgentResult:
    """Implement the observation-driven loop using a learner-owned model adapter.

    case has case_id/task/inputs/limits, with no expected answers. Bind model
    timeouts, tool calls, grouped messages, error recovery, limits and final
    evidence checks here. Define and document the model adapter's contract.
    Missing usage is None. Stop causes must remain distinguishable in your
    report even when mapped onto the evaluator's four terminal statuses.
    """
    raise NotImplementedError("Day19 Agent 核心由学习者独立实现")


async def evaluate_case(case: dict[str, Any], tools: ToolPort) -> AgentResult:
    """Bind a real or explicitly simulated model and invoke the learner core.

    CLI: python -m scripts.evaluate_agent --adapter
         course.projects.support_agent_runtime:evaluate_case --mode offline
    The mode flag labels a report; it neither creates nor verifies a model
    connection. Do not substitute author demos or fabricated successful output.
    """
    raise NotImplementedError("先绑定本人模型适配器，再接通评测入口")
