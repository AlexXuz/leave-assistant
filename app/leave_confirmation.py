"""Day11 作业二：处理确认接口的业务动作，绑定用户、草稿版本与内容。"""

from app.leave_confirmation_store import DraftRevisionConflict, DraftStateError, content_hash
from app.permission_service import TrustedAccessContext


def confirm_leave_draft(draft_id: str, expected_revision: int, access: TrustedAccessContext, store) -> dict:
    """只实现此函数；不改第一题，不调用模型，不写申请或扣余额。

    此入口假定由应用的“确认此版本”按钮/API动作调用，服务端提供access和store。
    普通对话或模型工具参数中的confirmed=true不能触发此入口。
    expected_revision来自用户刚查看的草稿版本，属于待校验输入；当前草稿必须由store读取。

    1. 验证access为TrustedAccessContext且user_id为非空白字符串，否则PermissionError。
       expected_revision必须是正整数（排除bool），否则ValueError。
    2. 在同一个with store.transaction():中完成余下步骤：
       row=store.lock_draft(draft_id, access.user_id)，helper检查所属用户并锁定读取。
       身份只能取后端access，不能取请求/模型中的user_id。
    3. row['revision'] != expected_revision：抛DraftRevisionConflict，旧版本确认不能覆盖新草稿。
    4. content_hash(row['payload']) != row['assessed_hash']：抛DraftRevisionConflict。
       代表当前内容不再对应通过预检的内容，不能只看状态就确认。
    5. row['status'] == 'CONFIRMED'：返回store.get_confirmation(draft_id)，重复点击不重复写。
       仍须先完成上面的用户、版本、内容检查，不能直接返回任意旧确认。
    6. status不是'READY_FOR_CONFIRMATION'：抛DraftStateError。
       不能确认BLOCKED、NEEDS_INFO、已提交等状态。
    7. 返回store.mark_confirmed(draft_id)，由helper保存本版本确认并更新状态。

    所有异常传播以回滚；不修改payload，不用模型声称“用户已确认”代替服务端确认记录。
    注意CONFIRMED只是用户确认此版本，不是SUBMITTED，更不是审批通过。
    本题内存存储只是可运行的接口替身，真实持久化及提交事务在后续接入。
    """
    if not isinstance(access, TrustedAccessContext) or not isinstance(access.user_id, str) or not access.user_id.strip():
        raise PermissionError("非法用户")
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError("expected_revision必须正整数")
    with store.transaction():
        row = store.lock_draft(draft_id, access.user_id)
        if row["revision"] != expected_revision:
            raise DraftRevisionConflict("旧版本确认不能覆盖新草稿")
        if content_hash(row["payload"]) != row["assessed_hash"]:
            raise DraftRevisionConflict("当前内容不再对应通过预检的内容")
        if row["status"] == "CONFIRMED":
            return store.get_confirmation(draft_id)
        if row["status"] != "READY_FOR_CONFIRMATION":
            raise DraftStateError("不能确认BLOCKED、NEEDS_INFO、已提交等状态")
        return store.mark_confirmed(draft_id)
