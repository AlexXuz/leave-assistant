"""助教验收：只读工具的执行边界，不调用模型、不加载Embedding、不连接数据库。"""

from pydantic import ValidationError

from app.leave_balance_tool import execute_balance_tool
from app.permission_service import TrustedAccessContext
from app.teaching_leave_service import TeachingLeaveService


def check():
    service = TeachingLeaveService()
    access_a = TrustedAccessContext("employee-demo-a", (), ())
    access_b = TrustedAccessContext("employee-demo-b", (), ())
    first = execute_balance_tool("get_my_leave_balance", '{"year":2026}', access_a, service)
    second = execute_balance_tool("get_my_leave_balance", '{"year":2026}', access_b, service)
    assert first["remaining_days"] == 9 and second["remaining_days"] == 3, "必须按可信用户隔离查询"
    assert service.calls == [("employee-demo-a", 2026), ("employee-demo-b", 2026)]
    missing = execute_balance_tool("get_my_leave_balance", '{"year":2025}', access_a, service)
    assert missing["status"] == "not_found" and missing["remaining_days"] is None, "缺记录不能伪造余额0"
    print("PASS：本人身份隔离、业务结果和缺记录语义。")
    cases = [
        ("other_function", '{"year":2026}', access_a, ValueError),
        ("get_my_leave_balance", '{"year":2026,"user_id":"employee-demo-b"}', access_a, ValidationError),
        ("get_my_leave_balance", '{"year":"2026"}', access_a, ValidationError),
        ("get_my_leave_balance", '{"year":true}', access_a, ValidationError),
        ("get_my_leave_balance", '{"year":9999}', access_a, ValidationError),
        ("get_my_leave_balance", '{}', access_a, ValidationError),
        ("get_my_leave_balance", 'not json', access_a, ValidationError),
        ("get_my_leave_balance", '{"year":2026}', {"user_id":"employee-demo-a"}, PermissionError),
        ("get_my_leave_balance", '{"year":2026}', TrustedAccessContext(" ", (), ()), PermissionError),
    ]
    for name, arguments, access, expected in cases:
        before = len(service.calls)
        try:
            execute_balance_tool(name, arguments, access, service)
        except expected:
            pass
        else:
            raise AssertionError("非法调用未被拒绝")
        assert len(service.calls) == before, "无效请求不应触达业务接口"
    print("PASS：工具允许列表、身份冒充与参数校验；拒绝时不调用业务接口。")

    class FailingService:
        def get_balance(self, user_id, year):
            raise TimeoutError("教学业务接口超时")

    try:
        execute_balance_tool("get_my_leave_balance", '{"year":2026}', access_a, FailingService())
    except TimeoutError:
        pass
    else:
        raise AssertionError("不能把业务异常转成成功余额")
    print("PASS：业务异常保留，不伪造成功。")


def main():
    try:
        check()
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    except (AssertionError, ValueError, TypeError, KeyError, PermissionError) as error:
        print(f"FAIL：{error}")
        return 1
    print("仅验证执行器；真实模型的tool_calls选择与结果回传将在下一步接通。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
