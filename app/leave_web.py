"""本地教学页面：演示账号登录，持久年假余额，多份申请共享账户额度。"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from threading import RLock

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import APIConnectionError, APIStatusError, APITimeoutError
from psycopg import Error as DatabaseError
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.course.examples.foundations.exercises import LeaveExtraction, build_messages, parse_model_output
from app.course.examples.foundations.leave_confirmation import confirm_leave_draft
from app.leave_confirmation_store import DraftRevisionConflict, DraftStateError
from app.course.examples.foundations.leave_submission import SubmissionBlocked, submit_leave
from app.leave_web_accounts import (BALANCE_YEAR, DEMO_PASSWORD, DEMO_USERS, WEB_RUN_ID, account_balance,
                                    create_account_draft, current_user, initialize_accounts, login, web_view)
from app.leave_workflow_store import PostgresLeaveStore
from app.permission_service import TrustedAccessContext
from app.pgvector_store import PROJECT_ROOT, connect_database
from scripts.ask_pdf_rag import tracked_model_call

STATIC = PROJECT_ROOT / "app/web"
COOKIE = "leave_lab_session"


class PrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    revision: int = Field(ge=1)


def create_app(run_id: str = WEB_RUN_ID, *, write_reports: bool = True) -> FastAPI:
    guard = RLock()
    ready = False
    app = FastAPI(title="LLM Engineer Lab · 办公助手示范")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.mount("/assets", StaticFiles(directory=STATIC), name="assets")

    def ensure_ready():
        nonlocal ready
        if not ready:
            with guard:
                if not ready:
                    try:
                        with connect_database() as connection:
                            initialize_accounts(connection, run_id)
                            with connection.transaction():
                                connection.execute((PROJECT_ROOT / 'infra/course_schema.sql').read_text(encoding='utf-8'),prepare=False)
                    except ValueError as error:
                        raise HTTPException(503,'业务实验需要先配置数据库并启动PostgreSQL；课程阅读可以直接使用。') from error
                    ready = True

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            expected = f"{request.url.scheme}://{request.headers.get('host')}"
            if request.headers.get("origin") != expected:
                return JSONResponse({"detail": "请从本机页面操作，跨站请求已拒绝。"}, status_code=403)
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                 "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    def user(request: Request) -> dict:
        if not request.cookies.get(COOKIE):
            raise HTTPException(401,'请先登录演示账号。')
        ensure_ready()
        with connect_database() as connection:
            row = current_user(connection, run_id, request.cookies.get(COOKIE, ""))
        if not row:
            raise HTTPException(401, "请先登录演示账号。")
        request.state.course_user = row
        return row

    def owned(draft_id: str, request: Request) -> tuple[dict, TrustedAccessContext]:
        person = user(request)
        with connect_database() as connection:
            row = connection.execute("SELECT draft_id,request_key FROM leave_workflow_lab.web_draft_requests WHERE run_id=%s AND draft_id=%s AND user_id=%s", (run_id, draft_id, person["user_id"])).fetchone()
        if row is None:
            raise HTTPException(404, "未找到当前账号的申请。")
        return row, TrustedAccessContext(person["user_id"], (), ())

    def read(draft_id, access):
        with connect_database() as connection:
            return web_view(connection, run_id, draft_id, access)

    def report(action, view, calls=None):
        if not write_reports:
            return
        path = PROJECT_ROOT / "reports" / f"leave-web-{action}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
        try:
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps({"action": action, "operator": "browser", "business_state": view, "model_calls": calls or []}, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    @app.exception_handler(APIConnectionError)
    async def model_connection_error(request, error):
        return JSONResponse({"detail": "模型连接失败，尚未生成草稿。请稍后重试。"}, status_code=503)

    @app.exception_handler(NotImplementedError)
    async def exercise_pending(request,error):
        return JSONResponse({'detail':'独立任务尚未实现，请先在IDE接好本课流程；示范通过不算本人完成。'},status_code=501)

    @app.exception_handler(APITimeoutError)
    async def model_timeout(request, error):
        return JSONResponse({"detail": "模型响应超时，尚未生成草稿。请稍后重试。"}, status_code=504)

    @app.exception_handler(APIStatusError)
    async def model_status_error(request, error):
        return JSONResponse({"detail": "模型服务暂时不可用，请稍后重试。"}, status_code=502)

    @app.exception_handler(DatabaseError)
    async def database_error(request, error):
        return JSONResponse({"detail": "数据库操作未完成。请确认Docker已启动，再刷新状态核对后重试。"}, status_code=503)

    @app.exception_handler(SubmissionBlocked)
    async def submission_blocked(request, error):
        return JSONResponse({"detail": "最新年假余额不足或业务复查未通过，请刷新账户余额，调整后重新生成。", "assessment": error.assessment}, status_code=409)

    @app.exception_handler(DraftRevisionConflict)
    async def revision_error(request, error):
        return JSONResponse({"detail": "草稿版本或内容已变化，请刷新并核对当前版本。"}, status_code=409)

    @app.exception_handler(DraftStateError)
    async def state_error(request, error):
        return JSONResponse({"detail": "当前状态不能执行此操作，请刷新查看。"}, status_code=409)

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "local_demo_accounts", "workflow_engine": "day11_python"}

    @app.get("/api/demo-accounts")
    def demo_accounts():
        ensure_ready()
        return {"password": DEMO_PASSWORD, "year": BALANCE_YEAR,
                "accounts": [{k: item[k] for k in ("username", "display_name", "department")} | {"initial_available": item["granted"] - item["used"]} for item in DEMO_USERS]}

    @app.post("/api/login")
    def sign_in(payload: LoginRequest, request: Request, response: Response):
        ensure_ready()
        with connect_database() as connection:
            token = login(connection, run_id, payload.username.strip(), payload.password, request.cookies.get(COOKIE))
        if not token:
            raise HTTPException(401, "账号或密码不正确。")
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=7 * 86400)
        return {"logged_in": True}

    @app.post("/api/logout")
    def sign_out(request: Request, response: Response):
        ensure_ready()
        token = request.cookies.get(COOKIE, "")
        with connect_database() as connection:
            connection.execute("DELETE FROM leave_workflow_lab.web_sessions WHERE run_id=%s AND token_hash=%s", (run_id, hashlib.sha256(token.encode()).hexdigest()))
        response.delete_cookie(COOKIE)
        return {"logged_in": False}

    @app.get("/api/me")
    def me(request: Request):
        person = user(request)
        with connect_database() as connection:
            balance = account_balance(connection, run_id, person["user_id"])
        return {"user": person, "balance": balance, "supported_leave_types": ["ANNUAL"]}

    @app.get("/api/drafts")
    def history(request: Request):
        person = user(request)
        access = TrustedAccessContext(person["user_id"], (), ())
        with connect_database() as connection:
            rows = connection.execute("SELECT draft_id FROM leave_workflow_lab.web_draft_requests WHERE run_id=%s AND user_id=%s ORDER BY created_at DESC LIMIT 30", (run_id, person["user_id"])).fetchall()
            return [web_view(connection, run_id, row["draft_id"], access) for row in rows]

    @app.post("/api/drafts", status_code=201)
    def prepare(payload: PrepareRequest, request: Request):
        person = user(request)
        if not payload.text.strip():
            raise HTTPException(422, "请输入请假需求。")
        access = TrustedAccessContext(person["user_id"], (), ())
        call = {"purpose": "extract", "prompt_version": "leave-parse-v2"}
        try:
            # 现有教学日志适配器捕获stdout，只串行化这段模型调用，不在SQL事务里等待网络。
            with guard:
                raw = tracked_model_call(build_messages(payload.text, datetime.now(timezone(timedelta(hours=8))).isoformat()), call, prompt_version="leave-parse-v2")
            parsed = parse_model_output(raw)
            draft = LeaveExtraction.model_validate({name: parsed[name] for name in ("leaveType", "startDate", "endDate", "reason")})
        except (ValidationError, ValueError) as error:
            raise HTTPException(502, "模型提取结果未通过校验，请补充明确的假种、日期和理由后重试。") from error
        # 身份在请求开始时由服务端会话绑定，模型无法指定或切换账号。
        with connect_database() as connection:
            view = create_account_draft(connection, run_id, access, draft)
        report("prepare", view, [call])
        return view

    @app.get("/api/drafts/{draft_id}")
    def show(draft_id: str, request: Request):
        row, access = owned(draft_id, request)
        return read(draft_id, access)

    def act(action: str, draft_id: str, payload: RevisionRequest, request: Request):
        row, access = owned(draft_id, request)
        with connect_database() as connection:
            store = PostgresLeaveStore(connection, run_id)
            if action == "confirm":
                confirm_leave_draft(draft_id, payload.revision, access, store)
            else:
                submit_leave(draft_id, payload.revision, row["request_key"], access, store)
            view = web_view(connection, run_id, draft_id, access)
        report(action, view)
        return view

    @app.post("/api/drafts/{draft_id}/confirm")
    def confirm(draft_id: str, payload: RevisionRequest, request: Request):
        return act("confirm", draft_id, payload, request)

    @app.post("/api/drafts/{draft_id}/submit")
    def submit(draft_id: str, payload: RevisionRequest, request: Request):
        return act("submit", draft_id, payload, request)

    @app.post("/api/drafts/{draft_id}/route-preview")
    def preview_route(draft_id: str, request: Request):
        from app.leave_graph_routing import route_leave_workflow
        row, access = owned(draft_id, request)
        view = read(draft_id, access)
        state = {"draft_status": view["draft_status"], "missing_fields": view["missing_fields"],
                 "application_id": view["application"]["application_id"] if view["application"] else None}
        try:
            route = route_leave_workflow(state)
        except NotImplementedError as error:
            raise HTTPException(501, "Day12路由函数尚未实现；当前页面的Day11业务流程仍可正常使用。") from error
        except ValueError as error:
            raise HTTPException(422, "路由判断拒绝了当前状态，请核对函数分支或重新预检。") from error
        if route not in {"request_details", "explain_block", "wait_confirmation", "submit", "show_result"}:
            raise HTTPException(422, "路由函数返回了未约定的节点名，请检查你的实现。")
        return {"state": state, "next_node": route, "executed": False}

    from app.course.web import mount_course
    mount_course(app, user, owned, run_id, ensure_ready, guard)
    return app


app = create_app()
