"""助教验收：草稿天数与余额预检；不调用模型、不写库。"""

from copy import deepcopy

from app import leave_draft as exercise
from app import leave_draft_preview as preview
from app.exercises import LeaveExtraction
from app.permission_service import TrustedAccessContext
from app.teaching_leave_service import TeachingLeaveService

BASE = {"leaveType": "ANNUAL", "startDate": "2026-11-02", "endDate": "2026-11-05", "reason": "处理家事"}


def check():
    draft = LeaveExtraction.model_validate(BASE)
    service = TeachingLeaveService()
    a = TrustedAccessContext("employee-demo-a", (), ())
    b = TrustedAccessContext("employee-demo-b", (), ())
    first = preview.prepare_leave_preview(draft, a, service)
    second = preview.prepare_leave_preview(draft, b, service)
    assert first["assessment"] == exercise.decision("READY_FOR_CONFIRMATION", "CHECKS_PASSED", days=4, remaining=9)
    assert second["assessment"] == exercise.decision("BLOCKED", "INSUFFICIENT_BALANCE", days=4, remaining=3)
    assert service.calls == [("employee-demo-a", 2026), ("employee-demo-b", 2026)]
    assert not first["submitted"] and not second["submitted"]
    assert draft.model_dump(mode="json") == BASE
    print("PASS：同一四天草稿按本人余额分别待确认/余额不足；没有提交或扣减。")

    for changes, status, code, missing in [
        ({"reason": None}, "NEEDS_INFO", "MISSING_FIELDS", ["reason"]),
        ({"startDate": None, "endDate": None}, "NEEDS_INFO", "MISSING_FIELDS", ["startDate", "endDate"]),
        ({"leaveType": "SICK"}, "BLOCKED", "LEAVE_TYPE_UNSUPPORTED", []),
        ({"startDate": "2026-12-31", "endDate": "2027-01-02"}, "BLOCKED", "CROSS_YEAR_UNSUPPORTED", []),
    ]:
        current = LeaveExtraction.model_validate({**BASE, **changes})
        before = len(service.calls)
        result = preview.prepare_leave_preview(current, a, service)
        assert result["assessment"] == exercise.decision(status, code, missing=missing)
        assert len(service.calls) == before, "不完整或不支持的草稿不应查询余额"
    print("PASS：缺字段、不支持假种及跨年草稿提前分流，不查询错误余额。")

    assert exercise.assess_leave_draft(draft) == exercise.decision("NEEDS_BALANCE", "BALANCE_REQUIRED", days=4)
    balance = service.get_balance("employee-demo-b", 2026)
    for remaining, status, code in [(4, "READY_FOR_CONFIRMATION", "CHECKS_PASSED"), (0, "BLOCKED", "INSUFFICIENT_BALANCE")]:
        value = {**balance, "remaining_days": remaining}
        assert exercise.assess_leave_draft(draft, value) == exercise.decision(status, code, days=4, remaining=remaining)
    for value in [{"status": "not_found", "remaining_days": None}, {"status": "error"},
                  {**balance, "year": 2025}, {**balance, "remaining_days": True}, {**balance, "unit": "小时"}]:
        original = deepcopy(value)
        assert exercise.assess_leave_draft(draft, value) == exercise.decision("BLOCKED", "BALANCE_UNAVAILABLE", days=4)
        assert value == original
    print("PASS：等于余额可待确认、0余额不足、无记录/故障/响应不匹配不能放行。")

    reversed_draft = LeaveExtraction.model_validate({**BASE, "startDate": "2026-11-06"})
    try:
        exercise.assess_leave_draft(reversed_draft, balance)
    except ValueError:
        pass
    else:
        raise AssertionError("日期倒置未被拒绝")

    class TimeoutService:
        def get_balance(self, user_id, year):
            raise TimeoutError("教学业务超时")

    assert preview.prepare_leave_preview(draft, a, TimeoutService())["assessment"]["code"] == "BALANCE_UNAVAILABLE"
    print("PASS：日期错误及业务超时不会变成成功草稿。")


def main():
    try:
        check()
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    except (AssertionError, ValueError, TypeError, KeyError) as error:
        print(f"FAIL：{error}")
        return 1
    print("仅验证草稿预检；用户确认、数据库提交、提交时复查和幂等仍待后续实现。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
