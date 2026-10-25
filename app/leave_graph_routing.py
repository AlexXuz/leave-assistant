"""Day12 第一题：决定流程下一步，只读状态、不执行业务动作。"""

from typing import Literal, TypedDict
from app.leave_workflow_runtime import DraftStatus

NextNode = Literal["request_details", "explain_block", "wait_confirmation", "submit", "show_result"]


class LeaveRouteState(TypedDict):
    """服务端从数据库构造；application_id是已提交事实，不是模型生成的编号。"""
    draft_status: DraftStatus
    missing_fields: list[str]
    application_id: str | None


def route_leave_workflow(state: LeaveRouteState) -> NextNode:
    """学习者实现此函数，下一课会把它用作StateGraph的条件边。

    先区分已完成，再按状态决定去向：
    1. draft_status为SUBMITTED：必须有非空application_id，返回show_result。
       SUBMITTED却没申请编号是状态不一致，抛ValueError，不重新提交。
    2. 其他状态却有application_id也抛ValueError，不猜测实际状态。
    3. missing_fields非空：返回request_details，不确认或提交。
    4. BLOCKED：explain_block。
    5. READY_FOR_CONFIRMATION：wait_confirmation。
    6. CONFIRMED：submit（只是返回下一节点名，不在这里调用submit_leave）。
    7. 其余状态（例如NEEDS_ASSESSMENT却无缺失字段）抛ValueError，等待重新预检。

    不修改state；不查数据库、不调用模型、不自动替用户确认。
    返回wait_confirmation只是路由选择；真正interrupt/检查点/恢复在下一题接入。
    可在网页“学习观察→检查我的路由”查看真实草稿的输出。
    """
    raise NotImplementedError("根据服务端状态选择下一节点")
