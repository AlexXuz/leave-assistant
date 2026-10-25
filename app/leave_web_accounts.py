"""助教提供：本机固定演示账号，共享持久额度；不改学习者年假业务函数。"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.course.examples.foundations.exercises import LeaveExtraction
from app.leave_confirmation_store import content_hash
from app.course.examples.foundations.leave_draft import assess_leave_draft
from app.leave_workflow_runtime import read_workflow
from app.leave_workflow_store import PostgresLeaveStore
from app.permission_service import TrustedAccessContext
from app.pgvector_store import PROJECT_ROOT

WEB_RUN_ID = "llm-engineer-lab-starter"
BALANCE_YEAR = 2026
DEMO_PASSWORD = "demo123"  # 仅虚构本地教学账号，页面明确展示。
DEMO_USERS = (
    {"username": "zhangsan", "display_name": "张三", "department": "研发部", "granted": 10, "used": 1},
    {"username": "lisi", "display_name": "李四", "department": "财务部", "granted": 10, "used": 7},
    {"username": "wangwu", "display_name": "王五", "department": "运营部", "granted": 10, "used": 10},
    {"username": "zhaoliu", "display_name": "赵六", "department": "产品部", "granted": 20, "used": 5},
)


def password_digest(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 160_000).hex()


def initialize_accounts(connection, run_id: str):
    """只插入不存在的账号/额度，重启和重新登录绝不重置余额。"""
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("web-init:" + run_id,))
        for source in ("leave_workflow_schema.sql", "leave_web_accounts.sql"):
            connection.execute((PROJECT_ROOT / "infra" / source).read_text(encoding="utf-8"), prepare=False)
        connection.execute("INSERT INTO leave_workflow_lab.runs(id) VALUES(%s) ON CONFLICT DO NOTHING", (run_id,))
        for item in DEMO_USERS:
            user_id = "web-" + item["username"]
            existing = connection.execute("SELECT 1 FROM leave_workflow_lab.web_users WHERE run_id=%s AND user_id=%s", (run_id, user_id)).fetchone()
            if not existing:
                salt = secrets.token_hex(16)
                connection.execute("INSERT INTO leave_workflow_lab.web_users VALUES(%s,%s,%s,%s,%s,%s,%s)",
                                   (run_id, user_id, item["username"], item["display_name"], item["department"], salt, password_digest(DEMO_PASSWORD, salt)))
            connection.execute("INSERT INTO leave_workflow_lab.accounts(run_id,user_id,year,granted_days,used_days) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                               (run_id, user_id, BALANCE_YEAR, item["granted"], item["used"]))


def login(connection, run_id: str, username: str, password: str, old_token: str | None) -> str | None:
    row = connection.execute("SELECT user_id,password_salt,password_hash FROM leave_workflow_lab.web_users WHERE run_id=%s AND username=%s", (run_id, username)).fetchone()
    if row is None or not hmac.compare_digest(password_digest(password, row["password_salt"]), row["password_hash"]):
        return None
    token = secrets.token_urlsafe(32)
    with connection.transaction():
        if old_token:
            connection.execute("DELETE FROM leave_workflow_lab.web_sessions WHERE run_id=%s AND token_hash=%s", (run_id, hashlib.sha256(old_token.encode()).hexdigest()))
        connection.execute("INSERT INTO leave_workflow_lab.web_sessions VALUES(%s,%s,%s,%s)",
                           (run_id, hashlib.sha256(token.encode()).hexdigest(), row["user_id"], datetime.now(timezone.utc) + timedelta(days=7)))
    return token


def current_user(connection, run_id: str, token: str) -> dict | None:
    if not token or len(token) > 128:
        return None
    return connection.execute("SELECT u.user_id,u.username,u.display_name,u.department FROM leave_workflow_lab.web_sessions s JOIN leave_workflow_lab.web_users u ON u.run_id=s.run_id AND u.user_id=s.user_id WHERE s.run_id=%s AND s.token_hash=%s AND s.expires_at>now()",
                              (run_id, hashlib.sha256(token.encode()).hexdigest())).fetchone()


def account_balance(connection, run_id: str, user_id: str, year: int = BALANCE_YEAR) -> dict | None:
    row = connection.execute("SELECT year,granted_days,used_days,reserved_days,granted_days-used_days-reserved_days AS remaining_days FROM leave_workflow_lab.accounts WHERE run_id=%s AND user_id=%s AND year=%s", (run_id, user_id, year)).fetchone()
    return {**row, "leave_type": "ANNUAL", "unit": "天"} if row else None


def web_view(connection, run_id: str, draft_id: str, access: TrustedAccessContext) -> dict:
    view = read_workflow(connection, run_id, draft_id, access)
    data = view.model_dump(mode="json")
    assessment = assess_leave_draft(view.draft)
    if assessment["status"] == "NEEDS_BALANCE":
        balance = account_balance(connection, run_id, access.user_id, view.draft.startDate.year)
        assessment = assess_leave_draft(view.draft, {**balance, "status": "ok"} if balance else {"status": "not_found"})
    data.update(assessment=assessment, balance_leave_type="ANNUAL", balance_year=view.draft.startDate.year if view.draft.startDate else None)
    if view.draft.leaveType != "ANNUAL":
        data.update(remaining_days=None, reserved_days=None, used_days=None)
    return data


def create_account_draft(connection, run_id: str, access: TrustedAccessContext, draft: LeaveExtraction) -> dict:
    draft_id = "draft-" + uuid4().hex
    store = PostgresLeaveStore(connection, run_id)
    with store.transaction():
        assessment = assess_leave_draft(draft)
        if assessment["status"] == "NEEDS_BALANCE":
            assessment = assess_leave_draft(draft, store.lock_balance(access.user_id, draft.startDate.year))
        status = {"READY_FOR_CONFIRMATION": "READY_FOR_CONFIRMATION", "BLOCKED": "BLOCKED", "NEEDS_INFO": "NEEDS_ASSESSMENT"}[assessment["status"]]
        payload = draft.model_dump(mode="json")
        connection.execute("INSERT INTO leave_workflow_lab.drafts VALUES(%s,%s,%s,1,%s,%s,%s)",
                           (run_id, draft_id, access.user_id, status, Jsonb(payload), content_hash(payload) if status == "READY_FOR_CONFIRMATION" else ""))
        connection.execute("INSERT INTO leave_workflow_lab.web_draft_requests(run_id,draft_id,user_id,request_key) VALUES(%s,%s,%s,%s)",
                           (run_id, draft_id, access.user_id, secrets.token_urlsafe(24)))
    return web_view(connection, run_id, draft_id, access)
