"""助教提供的存储接口/字典字段说明，供IDE补全与静态检查；不执行运行时校验。"""

from contextlib import AbstractContextManager
from typing import Literal, Protocol, TypedDict


class LeavePayload(TypedDict):
    leaveType: Literal["ANNUAL", "SICK", "PERSONAL"] | None
    startDate: str | None
    endDate: str | None
    reason: str | None


class SubmissionRecord(TypedDict):
    """find_submission查到的完整申请；无记录时方法返回None。"""

    application_id: str
    draft_id: str
    user_id: str
    revision: int
    content_hash: str
    payload: LeavePayload
    requested_days: int
    idempotency_key: str
    status: Literal["PENDING_APPROVAL"]


class WorkflowDraft(TypedDict):
    draft_id: str
    user_id: str
    revision: int
    status: Literal["NEEDS_ASSESSMENT", "READY_FOR_CONFIRMATION", "CONFIRMED", "SUBMITTED", "BLOCKED"]
    payload: LeavePayload
    assessed_hash: str


class ConfirmationRecord(TypedDict):
    draft_id: str
    user_id: str
    revision: int
    content_hash: str
    status: Literal["CONFIRMED"]


class LeaveWorkflowStore(Protocol):
    """类似Java接口，描述调用方需要的方法；实际SQL仍由PostgresLeaveStore实现。"""

    def transaction(self) -> AbstractContextManager[None]: ...
    def lock_request(self, user_id: str, key: str) -> None: ...
    def find_submission(self, user_id: str, key: str) -> SubmissionRecord | None: ...
    def lock_draft(self, draft_id: str, user_id: str) -> WorkflowDraft: ...
    def get_confirmation(self, draft_id: str) -> ConfirmationRecord: ...
    def mark_confirmed(self, draft_id: str) -> ConfirmationRecord: ...
    def lock_balance(self, user_id: str, year: int) -> dict: ...
    def reserve_balance(self, user_id: str, year: int, days: int) -> None: ...
    def save_submission(self, draft_id: str, key: str, days: int) -> SubmissionRecord: ...
