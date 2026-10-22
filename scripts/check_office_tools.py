"""助教验收双工具调度：固定替身检索，不加载模型、不连接数据库。"""

from unittest.mock import patch

from pydantic import ValidationError

from app import office_tools as exercise
from app.permission_service import TrustedAccessContext
from app.teaching_leave_service import TeachingLeaveService


def check():
    access = TrustedAccessContext("employee-demo-b", ("server-policy-source",), ("engineering",))
    service = TeachingLeaveService()
    source = "server-policy-source"
    # 余额分支必须复用已经验收的执行器；不触达制度检索。
    with patch.object(exercise, "execute_balance_tool", wraps=exercise.execute_balance_tool) as balance, \
            patch.object(exercise, "retrieve_visible") as retrieve:
        result = exercise.execute_office_tool("get_my_leave_balance", '{"year":2026}', access, source, service)
        assert result["remaining_days"] == 3
        balance.assert_called_once_with("get_my_leave_balance", '{"year":2026}', access, service)
        retrieve.assert_not_called()
    print("PASS：余额分支复用既有执行器，不检索制度。")

    chunk = {"id": "policy:2026-v1:2", "document_id": "policy", "title": "虚构制度",
             "version": "2026-v1", "heading": "审批", "content": "示例审批条件"}
    with patch.object(exercise, "retrieve_visible", return_value=[{"chunk": chunk, "score": 0.7}]) as retrieve, \
            patch.object(exercise, "execute_balance_tool") as balance:
        result = exercise.execute_office_tool("search_policy", '{"question":"  四天年假谁审批？  "}', access, source, service)
        retrieve.assert_called_once_with("四天年假谁审批？", source, access, top_k=2)
        assert result == {"source": "policy-search", "status": "ok", "evidence": [chunk]}
        balance.assert_not_called()
    print("PASS：制度分支保留服务端来源和身份，只取授权命中。")

    with patch.object(exercise, "retrieve_visible", return_value=[]) as retrieve:
        result = exercise.execute_office_tool("search_policy", '{"question":"未提供的制度？"}', access, source, service)
        assert result["status"] == "no_evidence" and result["evidence"] == []
        assert retrieve.call_count == 1, "空命中不得移除权限重查"
    cases = [
        ("search_policy", '{"question":"审批？","source_id":"other-source"}', ValidationError),
        ("search_policy", '{"question":"审批？","department_ids":["finance"]}', ValidationError),
        ("search_policy", '{"question":"审批？","user_id":"someone-else"}', ValidationError),
        ("search_policy", '{"question":" "}', ValidationError),
        ("search_policy", '{}', ValidationError),
        ("search_policy", '{"question":3}', ValidationError),
        ("search_policy", 'not json', ValidationError),
        ("unknown_tool", '{"year":2026}', ValueError),
    ]
    for name, arguments, expected in cases:
        with patch.object(exercise, "retrieve_visible") as retrieve, patch.object(exercise, "execute_balance_tool") as balance:
            try:
                exercise.execute_office_tool(name, arguments, access, source, service)
            except expected:
                pass
            else:
                raise AssertionError("无效请求没有被拒绝")
            retrieve.assert_not_called()
            balance.assert_not_called()
    print("PASS：空命中、伪造来源/身份/部门、非法参数和未知工具的边界。")

    for error in (PermissionError("不允许此来源"), RuntimeError("教学数据库故障")):
        with patch.object(exercise, "retrieve_visible", side_effect=error) as retrieve:
            try:
                exercise.execute_office_tool("search_policy", '{"question":"谁审批？"}', access, source, service)
            except type(error):
                pass
            else:
                raise AssertionError("权限或基础设施异常应继续传播")
            assert retrieve.call_count == 1
    print("PASS：异常传播，不回退到未授权数据源。")


def main():
    try:
        check()
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    except (AssertionError, ValueError, TypeError, KeyError, PermissionError) as error:
        print(f"FAIL：{error}")
        return 1
    print("仅验证调度与委托；真实双工具选择、数据库检索和最终回答待下一步验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
