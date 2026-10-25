"""Day11 作业一：纯业务草稿评估，不写库、不提交、不调用模型。"""
from app.paths import PROJECT_ROOT

from app.course.examples.foundations.exercises import LeaveExtraction, validate_date_range


def missing_fields(draft: LeaveExtraction) -> list[str]:
    """助教提供：从已校验的字段判断缺失，不信任模型给出的missingFields。"""
    return [name for name in ("leaveType", "startDate", "endDate", "reason") if getattr(draft, name) is None]


def decision(status, code, *, missing=None, days=None, remaining=None):
    """助教提供统一结果字段；仅便于观察状态，不生成确认凭据。"""
    return {"status": status, "code": code, "missing_fields": list(missing or []),
            "requested_days": days, "remaining_days": remaining}


def available_days(balance: dict, year: int) -> int | None:
    """助教提供：余额只接受本年份、年假、天数单位的正常业务响应。

    接口无记录、错误或格式不匹配都不能作为可靠余额；0是有效余额，不等于None。
    本课仅整天申请，返回半天等精度时先视为本适配器不支持。
    """
    if (balance.get("status") != "ok" or type(balance.get("year")) is not int
            or balance["year"] != year or balance.get("leave_type") != "ANNUAL" or balance.get("unit") != "天"):
        return None
    value = balance.get("remaining_days")
    return value if type(value) is int and value >= 0 else None


def assess_leave_draft(draft: LeaveExtraction, balance: dict | None = None) -> dict:
    """学习者只实现此函数，字段模型/结果拼装由助教提供。

    draft沿用Day1的LeaveExtraction（日期已解析为date）；balance由后端业务接口返回，
    不从用户或模型提取JSON接收余额。None表示尚未查询，not_found/error表示查询过但没有可靠余额。

    按顺序处理，使用decision helper返回统一结构：
    1. 复用validate_date_range(draft)，日期倒置抛ValueError，不转换为成功草稿。
    2. missing_fields(draft)非空：NEEDS_INFO / MISSING_FIELDS，missing=缺失列表。
    3. leaveType不是ANNUAL：BLOCKED / LEAVE_TYPE_UNSUPPORTED。
       本课余额接口仅支持年假，不能拿年假余额校验病假/事假。
    4. 开始/结束日期不同年份：BLOCKED / CROSS_YEAR_UNSUPPORTED，不只查开始年就放行。
    5. 后端计算days=(endDate-startDate).days+1，首尾均计入。
       这是已有Day3约定的整日、连续日历日教学计数；非生产工作日/节假日规则。
    6. balance是None：NEEDS_BALANCE / BALANCE_REQUIRED，days=计算天数。
    7. remaining=available_days(balance, startDate.year)。若是None：
       BLOCKED / BALANCE_UNAVAILABLE，days=计算天数，不能当作0余额。
    8. days > remaining：BLOCKED / INSUFFICIENT_BALANCE，传days和remaining。
    9. 否则READY_FOR_CONFIRMATION / CHECKS_PASSED，传days和remaining。

    helper例：decision('NEEDS_INFO','MISSING_FIELDS',missing=['reason'])。
    每步确定后立即return；不修改draft/balance，不在本函数查询、写入或扣减余额。
    READY_FOR_CONFIRMATION只表示本课预检通过；不是用户已确认、不是已提交/已获批。
    提交时必须重新查询并校验余额，不能把此时的预检结果当作永不过期的授权。
    """
    validate_date_range(draft)
    missing = missing_fields(draft)
    if missing:
        return decision(
            "NEEDS_INFO",
            "MISSING_FIELDS",
            missing=missing
        )
    if draft.leaveType != "ANNUAL":
        return decision(
            "BLOCKED",
            "LEAVE_TYPE_UNSUPPORTED"
        )
    if draft.startDate.year != draft.endDate.year:
        return decision(
            "BLOCKED",
            "CROSS_YEAR_UNSUPPORTED"
        )
    days = (draft.endDate - draft.startDate).days + 1
    if balance is None:
        return decision(
            "NEEDS_BALANCE",
            "BALANCE_REQUIRED",
            days=days
        )
    remaining = available_days(balance, draft.startDate.year)
    if remaining is None:
        return decision(
            "BLOCKED",
            "BALANCE_UNAVAILABLE",
            days=days
        )
    if days > remaining:
        return decision(
            "BLOCKED",
            "INSUFFICIENT_BALANCE",
            days=days,
            remaining=remaining
        )
    else:
        return decision(
            "READY_FOR_CONFIRMATION",
            "CHECKS_PASSED",
            days=days,
            remaining=remaining
        )
