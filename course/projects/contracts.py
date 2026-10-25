"""Independent-task ports: shapes are explicit; implementations remain learner-owned.

These are teaching interfaces, not runtime service implementations. Adapt existing
Day1–Day11 services outside their accepted source files. A Protocol describes what
can be called; it does not enforce authentication or transaction behavior.
"""
from __future__ import annotations
from typing import Any, Protocol, TypedDict


class DraftSnapshot(TypedDict):
    draft_id: str
    revision: int
    draft_status: str
    draft: dict
    missing_fields: list[str]
    remaining_days: int | None
    reserved_days: int
    application: dict | None


class WorkflowServices(Protocol):
    """Host binds account/draft/key; learner must not take them from model text."""
    def read_draft(self) -> DraftSnapshot: ...
    def confirm(self, revision: int) -> DraftSnapshot: ...
    def submit(self, revision: int, key: str) -> DraftSnapshot: ...


class ContextServices(Protocol):
    def read_snapshot(self) -> dict: ...
    def read_preference(self) -> dict: ...
    def delete_preference(self) -> None: ...


class ReportServices(Protocol):
    def read_monthly_report(self, month: str) -> dict: ...


class TraceEvent(TypedDict):
    request_id: str
    phase: str
    duration_ms: float
    outcome: str
    business_committed: bool | None


class QueryResult(TypedDict):
    query_id: str
    rows: list[dict]
    scope: str
    unit: str
    status: str


class TextModel(Protocol):
    def complete(self, messages: list[dict]) -> str: ...


class QueryServices(Protocol):
    """Adapter must implement role/view/transaction limits, not just a SQL string."""
    def execute_sql(self, sql: str, trusted_scope: str, statement_timeout_ms: int) -> QueryResult: ...


class TokenizerPort(Protocol):
    def __call__(self, text: str, **options: Any) -> dict: ...
