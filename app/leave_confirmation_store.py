"""助教提供：单进程内存事务存储，用于确认版本练习；不是持久化数据库。"""

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from threading import RLock


class DraftRevisionConflict(ValueError):
    pass


class DraftStateError(ValueError):
    pass


def content_hash(payload: dict) -> str:
    """确认绑定业务字段；不把模型措辞、余额快照或界面展示文本当作草稿内容。"""
    content = {name: payload[name] for name in ("leaveType", "startDate", "endDate", "reason")}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


class TeachingConfirmationStore:
    """提供transaction/lock_draft/mark_confirmed/get_confirmation，后续可替换真实存储。

    RLock只在本进程串行化练习；异常回滚内存快照，不提供跨进程或重启后持久性。
    """

    def __init__(self, drafts):
        self.drafts = {row["draft_id"]: deepcopy(row) for row in drafts}
        self.confirmations = {}
        self.confirm_write_count = 0
        self._active = False
        self._locked_ids = set()
        self._lock = RLock()

    @contextmanager
    def transaction(self):
        with self._lock:
            if self._active:
                raise RuntimeError("本教学存储不支持嵌套事务")
            snapshot = deepcopy((self.drafts, self.confirmations, self.confirm_write_count))
            self._active = True
            self._locked_ids = set()
            try:
                yield
            except Exception:
                self.drafts, self.confirmations, self.confirm_write_count = snapshot
                raise
            finally:
                self._active = False
                self._locked_ids = set()

    def lock_draft(self, draft_id, user_id):
        if not self._active:
            raise RuntimeError("必须在同一事务里读取并确认草稿")
        row = self.drafts.get(draft_id)
        if row is None or row["user_id"] != user_id:
            raise PermissionError("无权访问该草稿或草稿不存在")
        self._locked_ids.add(draft_id)
        return deepcopy(row)

    def get_confirmation(self, draft_id):
        if not self._active or draft_id not in self._locked_ids:
            raise RuntimeError("应先在事务中锁定本人草稿")
        if draft_id not in self.confirmations:
            raise DraftStateError("确认状态与服务端记录不一致")
        return deepcopy(self.confirmations[draft_id])

    def mark_confirmed(self, draft_id):
        if not self._active or draft_id not in self._locked_ids:
            raise RuntimeError("应先在事务中锁定本人草稿")
        row = self.drafts[draft_id]
        if row["status"] != "READY_FOR_CONFIRMATION":
            raise DraftStateError("当前草稿不能写入确认记录")
        confirmation = {"draft_id": draft_id, "user_id": row["user_id"],
                        "revision": row["revision"], "content_hash": content_hash(row["payload"]),
                        "status": "CONFIRMED"}
        self.confirmations[draft_id] = confirmation
        row["status"] = "CONFIRMED"
        self.confirm_write_count += 1
        return deepcopy(confirmation)


def teaching_draft():
    """固定已预检草稿，仅用于独立验证第二题，不调用第一题待实现函数。"""
    payload = {"leaveType": "ANNUAL", "startDate": "2026-11-02", "endDate": "2026-11-05", "reason": "处理家事"}
    return {"draft_id": "draft-demo-001", "user_id": "employee-demo-a", "revision": 1,
            "status": "READY_FOR_CONFIRMATION", "payload": payload, "assessed_hash": content_hash(payload)}
