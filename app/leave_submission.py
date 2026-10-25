"""Day11 作业三：确认后的申请提交、余额复查和成功请求幂等。"""

from app.exercises import LeaveExtraction
from app.leave_confirmation_store import DraftRevisionConflict, DraftStateError, content_hash
from app.leave_draft import assess_leave_draft
from app.permission_service import TrustedAccessContext
from app.leave_workflow_types import ConfirmationRecord, LeaveWorkflowStore, SubmissionRecord, WorkflowDraft


class IdempotencyConflict(ValueError):
    pass


class SubmissionBlocked(ValueError):
    def __init__(self, assessment):
        self.assessment = assessment
        super().__init__(assessment["code"])


def require_confirmation(row: WorkflowDraft, confirmation: ConfirmationRecord) -> None:
    """助教提供：确认只读取服务端记录，不接收模型/客户端提供的确认JSON。"""
    if (confirmation["draft_id"] != row["draft_id"] or confirmation["user_id"] != row["user_id"]
            or confirmation["revision"] != row["revision"]
            or confirmation["content_hash"] != content_hash(row["payload"])):
        raise DraftRevisionConflict("服务端确认记录不对应当前草稿")


def submit_leave(draft_id: str, expected_revision: int, idempotency_key: str,
                 access: TrustedAccessContext, store: LeaveWorkflowStore) -> SubmissionRecord:
    """只实现此函数，SQL和存储由助教提供；不改前两题，不调用模型。

    本课提交=创建待审批申请并预占天数，绝不是审批通过或实际休假已使用。
    参数只有草稿ID/用户看过的版本/请求幂等key；业务字段从服务端草稿读取。

    1. access应为可信上下文，user_id非空白字符串；否则PermissionError。
       expected_revision是正整数且非bool；idempotency_key为非空白字符串、长度<=128；否则ValueError。
    2. 余下全部放在同一with store.transaction():中：
       store.lock_request(access.user_id, idempotency_key) 串行化同一用户同一key。
       old=store.find_submission(access.user_id, idempotency_key)。若非None：
         old的draft_id/revision和本请求一致则原样return；否则抛IdempotencyConflict。
       成功请求重试先返回原结果，不再次检查已提交状态或占用余额。
    3. row=store.lock_draft(draft_id, access.user_id)，锁定并校验本人草稿。
       revision不等于expected_revision，或当前内容hash不等于assessed_hash：DraftRevisionConflict。
       row['status']必须为CONFIRMED，否则DraftStateError。
       同一草稿换新key再提交也会被SUBMITTED状态阻止，不另建第二笔申请。
    4. require_confirmation(row, store.get_confirmation(draft_id))，验证服务端确认对应本版本。
    5. draft=LeaveExtraction.model_validate(row['payload'])。
       balance=store.lock_balance(access.user_id, draft.startDate.year)，读并锁定最新额度。
       assessment=assess_leave_draft(draft, balance)，复用第一题重新预检。
       status不是READY_FOR_CONFIRMATION则raise SubmissionBlocked(assessment)，不能沿用旧余额。
    6. days=assessment['requested_days']；
       store.reserve_balance(access.user_id, draft.startDate.year, days) 预占额度；
       return store.save_submission(draft_id, idempotency_key, days) 创建申请并标记草稿已提交。

    异常传播，额度/申请/草稿状态一起回滚。SQL helper有唯一约束兜底。
    先锁请求key，再锁草稿，最后锁额度；不要在事务中调用LLM或外部HR网络接口。
    本实现额度与申请同处教学PostgreSQL事务，不能把它直接当作跨外部HR系统的分布式原子事务。
    """
    if (not isinstance(access, TrustedAccessContext)
            or not isinstance(access.user_id, str)
            or not access.user_id.strip()):
        raise PermissionError("非法用户")
    if (type(expected_revision) is not int
            or expected_revision < 1
            or not isinstance(idempotency_key, str)
            or not idempotency_key.strip()
            or len(idempotency_key) > 128):
        raise ValueError
    with store.transaction():
        store.lock_request(access.user_id, idempotency_key)
        old = store.find_submission(access.user_id, idempotency_key)
        if old is not None:
            if old["draft_id"] != draft_id or old["revision"] != expected_revision:
                raise IdempotencyConflict()
            return old
        row = store.lock_draft(draft_id, access.user_id)
        if row["revision"] != expected_revision or content_hash(row["payload"]) != row["assessed_hash"]:
            raise DraftRevisionConflict
        if row["status"] != "CONFIRMED":
            raise DraftStateError
        require_confirmation(row, store.get_confirmation(draft_id))
        draft = LeaveExtraction.model_validate(row["payload"])
        balance = store.lock_balance(access.user_id, draft.startDate.year)
        assessment = assess_leave_draft(draft, balance)
        if assessment["status"] != "READY_FOR_CONFIRMATION":
            raise SubmissionBlocked(assessment)
        days = assessment["requested_days"]
        store.reserve_balance(access.user_id, draft.startDate.year, days)
        return store.save_submission(draft_id, idempotency_key, days)
