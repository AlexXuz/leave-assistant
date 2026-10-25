"""Day10 双工具调度：复用只读业务接口与已有授权制度检索。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.leave_balance_tool import BALANCE_TOOL, execute_balance_tool
from app.permission_service import TrustedAccessContext, retrieve_visible


from app.course.examples.foundations.office_tools import PolicySearch  # Shared teaching interface.


POLICY_TOOL = {
    "type": "function",
    "function": {
        "name": "search_policy",
        "description": "检索公司制度中的申请条件、审批人、办理流程等规则，返回授权范围内的参考片段；不能查询员工个人余额或申请状态。",
        "parameters": PolicySearch.model_json_schema(),
    },
}
OFFICE_TOOLS = [BALANCE_TOOL, POLICY_TOOL]


def search_policy_tool(question: str, source_id: str, access: TrustedAccessContext) -> dict:
    """助教提供：直接复用授权检索，不额外调用聊天模型，不放宽权限补结果。"""
    if not isinstance(access, TrustedAccessContext) or not isinstance(access.user_id,
                                                                      str) or not access.user_id.strip():
        raise PermissionError("缺少可信登录上下文")
    hits = retrieve_visible(question, source_id, access, top_k=2)
    return {"source": "policy-search", "status": "ok" if hits else "no_evidence",
            "evidence": [hit["chunk"] for hit in hits]}


def execute_office_tool(
        name: str, arguments_json: str, access: TrustedAccessContext,
        policy_source_id: str, balance_service,
) -> dict:
    """只实现这个函数；不重新实现余额校验、检索SQL或模型调用。

    模型只提出name和arguments_json；其余三个参数由服务端注入。
    模型自己选择工具，你负责校验和执行，不用根据问题中的“余额/审批”等关键词路由。

    - name == 'get_my_leave_balance'：调用已有execute_balance_tool，
      name/arguments_json/access/balance_service原样传入，原样返回结果。
      不复制上一课的校验逻辑，不去查制度来推测余额。
    - name == 'search_policy'：用PolicySearch.model_validate_json校验参数，
      将query.question、policy_source_id、access传给search_policy_tool，原样返回。
      source_id及部门身份不能从模型参数里读，不能另建或修改access。
    - 其他工具名：抛ValueError，不执行任何工具。

    异常继续向上抛。空证据由helper返回no_evidence，不改查余额、不移除权限重查。
    本函数不调用聊天模型、不处理tool_call_id、不拼最终答案；这些属于外层编排。
    """
    raise NotImplementedError("请完成 execute_office_tool；输入输出与验收见网页课程")
