"""Day10 学习者作业：模型提出调用请求，后端负责受控执行。"""

from pydantic import BaseModel, ConfigDict, Field

from app.permission_service import TrustedAccessContext


from app.course.examples.foundations.leave_balance_tool import BalanceQuery  # Shared teaching interface.


BALANCE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_my_leave_balance",
        "description": "查询当前已登录用户指定年份的年假余额；不能查询其他员工，也不修改余额。",
        "parameters": BalanceQuery.model_json_schema(),
    },
}


def execute_balance_tool(name: str, arguments_json: str, access: TrustedAccessContext, service) -> dict:
    """只实现这个函数，别改已有RAG或模型调用函数。

    name/arguments_json 是模型返回的函数名和JSON参数字符串，均属于待校验输入。
    access 是后端认证层传入的可信上下文；本课仍用模拟登录，不是完整认证系统。
    service 是助教提供的教学业务接口，有 get_balance(user_id, year) 方法。

    按顺序处理：
    1. access 不是 TrustedAccessContext，或 user_id 为空/全空白，抛 PermissionError。
    2. 只接受 name == 'get_my_leave_balance'，其他名称抛 ValueError，不调用业务接口。
    3. 用 BalanceQuery.model_validate_json(arguments_json) 校验模型参数。
       JSON错误、未知字段、year类型/范围错误让Pydantic异常直接传播。
       即使参数偷偷带 user_id，也不能采用或静默忽略。
    4. 调用 service.get_balance(access.user_id, query.year)，原样返回业务结果。
       身份只取可信上下文，模型不能决定查谁；业务异常直接传播，不能伪造余额0。

    例：name='get_my_leave_balance', arguments_json='{"year":2026}'，
    可信登录employee-demo-a时，只能调用 service.get_balance('employee-demo-a', 2026)。
    本函数不写数据库、不调模型、不做关键词意图分类，也不执行动态eval/getattr。
    """
    raise NotImplementedError("请完成 execute_balance_tool；输入输出与验收见网页课程")
