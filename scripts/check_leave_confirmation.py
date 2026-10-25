"""助教验收第二题：内存事务替身，不依赖第一题实现、不调用模型或数据库。"""

from copy import deepcopy
from unittest.mock import patch

from app.leave_confirmation import confirm_leave_draft
from app.leave_confirmation_store import DraftRevisionConflict, DraftStateError, TeachingConfirmationStore, teaching_draft
from app.permission_service import TrustedAccessContext


def rejected(action, expected):
    try:
        action()
    except expected:
        return
    raise AssertionError("应拒绝的确认被放行")


def check():
    row = teaching_draft()
    access = TrustedAccessContext("employee-demo-a", (), ())
    store = TeachingConfirmationStore([row])
    first = confirm_leave_draft(row["draft_id"], 1, access, store)
    assert first == {"draft_id": row["draft_id"], "user_id": access.user_id, "revision": 1,
                     "content_hash": row["assessed_hash"], "status": "CONFIRMED"}
    assert store.drafts[row["draft_id"]]["status"] == "CONFIRMED"
    assert store.drafts[row["draft_id"]]["payload"] == row["payload"]
    assert confirm_leave_draft(row["draft_id"], 1, access, store) == first
    assert store.confirm_write_count == 1
    print("PASS：确认绑定本人、版本与内容；重复点击复用同一记录。")

    changed = deepcopy(row)
    changed["revision"] = 2
    changed["payload"]["endDate"] = "2026-11-06"
    changed["status"] = "NEEDS_ASSESSMENT"
    cases = [
        (changed, 1, access, DraftRevisionConflict),
        ({**row, "payload": {**row["payload"], "reason": "改后的理由"}}, 1, access, DraftRevisionConflict),
        ({**row, "status": "BLOCKED"}, 1, access, DraftStateError),
        ({**row, "status": "SUBMITTED"}, 1, access, DraftStateError),
        (row, 1, TrustedAccessContext("employee-demo-b", (), ()), PermissionError),
        (row, 1, {"user_id": "employee-demo-a"}, PermissionError),
        (row, 1, TrustedAccessContext(123, (), ()), PermissionError),
        (row, True, access, ValueError),
        (row, 1.0, access, ValueError),
        (row, 0, access, ValueError),
        (row, "1", access, ValueError),
    ]
    for current, expected_revision, current_access, error_type in cases:
        current_store = TeachingConfirmationStore([current])
        before = deepcopy(current_store.drafts)
        rejected(lambda: confirm_leave_draft(current["draft_id"], expected_revision, current_access, current_store), error_type)
        assert current_store.drafts == before and not current_store.confirmations
    print("PASS：旧版本、内容变更、无权身份、非法版本和不可确认状态被拒绝。")

    failing_store = TeachingConfirmationStore([row])
    original = failing_store.mark_confirmed

    def write_then_fail(draft_id):
        original(draft_id)
        raise RuntimeError("模拟确认写入后失败")

    with patch.object(failing_store, "mark_confirmed", side_effect=write_then_fail):
        rejected(lambda: confirm_leave_draft(row["draft_id"], 1, access, failing_store), RuntimeError)
    assert failing_store.drafts[row["draft_id"]] == row
    assert not failing_store.confirmations and failing_store.confirm_write_count == 0
    print("PASS：写入后失败回滚；确认记录与草稿状态保持一致。")


def main():
    try:
        check()
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    except (AssertionError, ValueError, TypeError, KeyError, PermissionError) as error:
        print(f"FAIL：{error}")
        return 1
    print("仅验证确认动作和内存事务替身；未实现生产认证、真实数据库提交或扣减额度。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
