"""助教SQL适配器：复用现有连接配置，独立run_id限定全部教学数据。"""

from contextlib import contextmanager
from collections.abc import Iterator
import json
from typing import cast
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.leave_confirmation_store import DraftRevisionConflict, DraftStateError, content_hash
from app.course.examples.foundations.leave_submission import SubmissionBlocked
from app.leave_workflow_types import ConfirmationRecord, SubmissionRecord, WorkflowDraft


class PostgresLeaveStore:
    def __init__(self, connection, run_id):
        self.connection, self.run_id = connection, run_id
        self._active = False
        self._drafts, self._balances, self._requests = {}, set(), set()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._active:
            raise RuntimeError("不支持嵌套业务事务")
        with self.connection.transaction():
            self.connection.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            self._active = True
            self._drafts, self._balances, self._requests = {}, set(), set()
            try:
                yield
            finally:
                self._active = False
                self._drafts, self._balances, self._requests = {}, set(), set()

    def _require_transaction(self):
        if not self._active:
            raise RuntimeError("必须在同一业务事务内调用")

    def lock_request(self, user_id: str, key: str) -> None:
        self._require_transaction()
        scope = json.dumps([self.run_id, user_id, key], ensure_ascii=False)
        self.connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (scope,))
        self._requests.add((user_id, key))

    def find_submission(self, user_id: str, key: str) -> SubmissionRecord | None:
        """返回申请记录（字段见SubmissionRecord），没有对应key时返回None。"""
        self._require_transaction()
        if (user_id, key) not in self._requests:
            raise RuntimeError("应先锁定本次请求key")
        return cast(SubmissionRecord | None, self.connection.execute(
            "SELECT application_id,draft_id,user_id,revision,content_hash,payload,requested_days,idempotency_key,status "
            "FROM leave_workflow_lab.applications WHERE run_id=%s AND user_id=%s AND idempotency_key=%s",
            (self.run_id, user_id, key),
        ).fetchone())

    def lock_draft(self, draft_id: str, user_id: str) -> WorkflowDraft:
        self._require_transaction()
        row = self.connection.execute(
            "SELECT draft_id,user_id,revision,status,payload,assessed_hash FROM leave_workflow_lab.drafts "
            "WHERE run_id=%s AND draft_id=%s AND user_id=%s FOR UPDATE", (self.run_id,draft_id,user_id),
        ).fetchone()
        if row is None:
            raise PermissionError("草稿不存在或无权访问")
        self._drafts[draft_id] = row
        return cast(WorkflowDraft, row)

    def _locked_draft(self, draft_id: str) -> WorkflowDraft:
        self._require_transaction()
        if draft_id not in self._drafts:
            raise RuntimeError("应先锁定本人草稿")
        return cast(WorkflowDraft, self._drafts[draft_id])

    def get_confirmation(self, draft_id: str) -> ConfirmationRecord:
        self._locked_draft(draft_id)
        row = self.connection.execute(
            "SELECT draft_id,user_id,revision,content_hash FROM leave_workflow_lab.confirmations "
            "WHERE run_id=%s AND draft_id=%s", (self.run_id,draft_id),
        ).fetchone()
        if row is None:
            raise DraftStateError("没有服务端确认记录")
        return {**row,"status":"CONFIRMED"}

    def mark_confirmed(self, draft_id: str) -> ConfirmationRecord:
        row = self._locked_draft(draft_id)
        if row["status"] != "READY_FOR_CONFIRMATION":
            raise DraftStateError("草稿不能确认")
        digest = content_hash(row["payload"])
        if digest != row["assessed_hash"]:
            raise DraftRevisionConflict("内容不对应预检")
        self.connection.execute(
            "INSERT INTO leave_workflow_lab.confirmations(run_id,draft_id,user_id,revision,content_hash) VALUES(%s,%s,%s,%s,%s)",
            (self.run_id,draft_id,row["user_id"],row["revision"],digest),
        )
        self.connection.execute("UPDATE leave_workflow_lab.drafts SET status='CONFIRMED' WHERE run_id=%s AND draft_id=%s", (self.run_id,draft_id))
        row["status"] = "CONFIRMED"
        return self.get_confirmation(draft_id)

    def lock_balance(self, user_id: str, year: int) -> dict:
        self._require_transaction()
        row = self.connection.execute(
            "SELECT granted_days-used_days-reserved_days AS remaining_days FROM leave_workflow_lab.accounts "
            "WHERE run_id=%s AND user_id=%s AND year=%s FOR UPDATE", (self.run_id,user_id,year),
        ).fetchone()
        if row is None:
            return {"status":"not_found","remaining_days":None}
        self._balances.add((user_id,year))
        return {"status":"ok","remaining_days":row["remaining_days"],"year":year,"leave_type":"ANNUAL","unit":"天"}

    def reserve_balance(self, user_id: str, year: int, days: int) -> None:
        self._require_transaction()
        if (user_id,year) not in self._balances or type(days) is not int or days < 1:
            raise RuntimeError("应先锁定额度并计算正整数天数")
        row = self.connection.execute(
            "UPDATE leave_workflow_lab.accounts SET reserved_days=reserved_days+%s "
            "WHERE run_id=%s AND user_id=%s AND year=%s AND granted_days-used_days-reserved_days >= %s RETURNING reserved_days",
            (days,self.run_id,user_id,year,days),
        ).fetchone()
        if row is None:
            raise SubmissionBlocked({"code":"INSUFFICIENT_BALANCE"})

    def save_submission(self, draft_id: str, key: str, days: int) -> SubmissionRecord:
        row = self._locked_draft(draft_id)
        if row["status"] != "CONFIRMED" or (row["user_id"],key) not in self._requests:
            raise DraftStateError("提交状态或请求key不匹配")
        application_id = "application-" + uuid4().hex
        self.connection.execute(
            "INSERT INTO leave_workflow_lab.applications(run_id,application_id,draft_id,user_id,revision,content_hash,payload,requested_days,idempotency_key,status) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING_APPROVAL')",
            (self.run_id,application_id,draft_id,row["user_id"],row["revision"],content_hash(row["payload"]),Jsonb(row["payload"]),days,key),
        )
        self.connection.execute("UPDATE leave_workflow_lab.drafts SET status='SUBMITTED' WHERE run_id=%s AND draft_id=%s", (self.run_id,draft_id))
        row["status"] = "SUBMITTED"
        # INSERT成功后，此key的记录在本事务中必然存在。
        return cast(SubmissionRecord, self.find_submission(row["user_id"],key))
