"""助教编排：用服务端身份查询余额，向学习者纯函数提供业务数据。"""

from app.exercises import LeaveExtraction
from app.leave_draft import assess_leave_draft
from app.permission_service import TrustedAccessContext


def prepare_leave_preview(draft: LeaveExtraction, access: TrustedAccessContext, service) -> dict:
    if not isinstance(access, TrustedAccessContext) or not isinstance(access.user_id, str) or not access.user_id.strip():
        raise PermissionError("缺少可信登录身份")
    assessment = assess_leave_draft(draft)
    balance = None
    if assessment["status"] == "NEEDS_BALANCE":
        try:
            balance = service.get_balance(access.user_id, draft.startDate.year)
        except TimeoutError:
            balance = {"status": "error", "code": "BUSINESS_TIMEOUT"}
        assessment = assess_leave_draft(draft, balance)
    return {"draft": draft.model_dump(mode="json"), "assessment": assessment,
            "balance": balance, "submitted": False}
