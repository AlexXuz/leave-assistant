"""Day17 learner workspace: async execution and persistent event subscription.

Read course/tasks/async_agent_runtime.md. This is not an Agent decision loop,
not a distributed queue, and not an implementation of authentication.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, TypedDict


class ToolCall(TypedDict):
    tool_call_id: str
    name: str
    arguments: dict


class ToolResult(TypedDict):
    tool_call_id: str
    status: Literal["ok", "error", "timeout", "cancelled"]
    data: dict | None
    error_code: str | None
    duration_ms: float


@dataclass(frozen=True)
class ExecutionLimits:
    max_concurrency: int
    total_timeout_seconds: float
    per_call_timeout_seconds: float


class ToolInvoker(Protocol):
    async def __call__(self, call: ToolCall, *, timeout_seconds: float) -> dict:
        """Async, authorized read-only tool adapter with real transport timeouts."""
        ...


class StoredEvent(TypedDict):
    seq: int
    event: str
    payload: dict


class EventStore(Protocol):
    async def authorize(self, job_id: str, trusted_principal: str) -> None:
        """Raise when the host-derived principal does not own the task."""
        ...

    async def read_after(self, job_id: str, after_id: int) -> list[StoredEvent]:
        """Read persisted events in increasing sequence order."""
        ...

    async def state(self, job_id: str) -> dict:
        """Return task state and final event sequence for race-free draining."""
        ...


async def execute_tool_batch(
    calls: Sequence[ToolCall],
    invoke: ToolInvoker,
    limits: ExecutionLimits,
    cancel_requested: asyncio.Event,
) -> list[ToolResult]:
    """Bound independent calls, count queue time, propagate cancellation safely.

    Return results in input order. Validate duplicate IDs and limits before I/O.
    External cancellation propagates after cleanup; expected tool errors may
    become structured results. Do not hide programmer errors as successful data.
    """
    raise NotImplementedError("Day17：本人异步工具执行器尚未实现")


def stream_job_events(
    job_id: str,
    after_id: int,
    trusted_principal: str,
    events: EventStore,
) -> AsyncIterator[str]:
    """Return an async SSE iterator after authorization and persisted replay.

    Implement an async generator or return one from here. Do not execute tools
    on subscription. Drain the final stored event before ending the stream.
    """
    raise NotImplementedError("Day17：本人持久事件订阅尚未实现")
