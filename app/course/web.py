"""课程阅读页与固定实验路由。身份复用现有登录会话，课程源码不由浏览器上传执行。"""
import ast
import asyncio
from collections import deque
from datetime import datetime
import html
import importlib
import json
from pathlib import Path
import subprocess
import sys
from threading import Lock
import time
from uuid import uuid4
from urllib.parse import urlencode, urlsplit, unquote

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field
from psycopg.errors import UndefinedColumn, UndefinedTable, SyntaxError as SQLSyntaxError, DivisionByZero, QueryCanceled, InsufficientPrivilege

from app.course.analytics import SqlPlan, execute_query, sql_messages
from app.course.memory import preference
from app.course import jobs
from app.course.assessment import assess_day, issue_challenge
from app.course.mcp_client import run_sync as mcp_client
from app.course.skill_runtime import execute_report
from app.course.state_graph import graph_operation
from app.leave_web_accounts import account_balance
from app.pgvector_store import PROJECT_ROOT, connect_database
from app.permission_service import TrustedAccessContext
from app.course.examples.context_selection import select_context
from scripts.ask_pdf_rag import tracked_model_call

COURSE=PROJECT_ROOT/'course'
_md=MarkdownIt('commonmark',{'html':False}).enable('table')
_training_gate=Lock()


def assignment_target(item,field='assignment'):
    """Expose the existing homework file, without importing or rewriting learner code."""
    path=(PROJECT_ROOT/item[field]).resolve()
    if not path.is_relative_to(PROJECT_ROOT) or not path.is_file():
        raise HTTPException(404,'作业文件不存在')
    target={'relative_path':item[field],'absolute_path':str(path),
            'kind':'python' if path.suffix=='.py' else 'document','functions':[]}
    if path.suffix=='.py':
        try:
            tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            target['functions']=[{'name':node.name,'line':node.lineno} for node in tree.body
                                 if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))]
        except SyntaxError as error:
            target['syntax_error']={'line':error.lineno,'message':error.msg}
    return target


class Choice(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    mode: str='reference'


class GraphAction(Choice):
    action: str='start'
    revision: int | None=None


class Turn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    user: str=Field(max_length=3000)
    assistant: str=Field(max_length=3000)


class ContextRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question: str=Field(min_length=1,max_length=1000)
    turns: list[Turn]=Field(default_factory=list,max_length=30)
    budget_chars: int=Field(default=1600,ge=200,le=20000)


class PreferenceRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tone: str | None=None
    delete: bool=False


class BIRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question: str=Field(default='统计2026年10月已批准的年假天数，按部门汇总。',max_length=1000)
    sql: str | None=Field(default=None,max_length=4000)


class AgentRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=1,max_length=600)


def mount_course(app,user,owned,run_id,ensure_ready,model_guard):
    traces=deque(maxlen=300)

    @app.middleware('http')
    async def trace_request(request: Request,call_next):
        started=time.perf_counter();identifier=uuid4().hex
        response=await call_next(request)
        person=getattr(request.state,'course_user',None)
        if person:
            traces.append({'request_id':identifier,'user_id':person['user_id'],'method':request.method,'path':request.url.path,'status':response.status_code,
                           'duration_ms':round((time.perf_counter()-started)*1000,2),'time':datetime.now().isoformat()})
        response.headers['X-Request-ID']=identifier
        return response

    def person(request):
        value=user(request);request.state.course_user=value
        return value

    def entries():
        return json.loads((COURSE/'manifest.json').read_text(encoding='utf-8'))['lessons']

    def entry(day):
        match=next((x for x in entries() if x['day']==day),None)
        if not match:
            raise HTTPException(404,'课程不存在')
        return match

    def render_file(relative):
        path=(PROJECT_ROOT/relative).resolve()
        if not path.is_relative_to(PROJECT_ROOT) or not path.is_file():
            raise HTTPException(404,'课程文件不存在')
        source=path.read_text(encoding='utf-8-sig')
        if path.suffix!='.md':
            return '<pre><code>'+html.escape(source)+'</code></pre>'
        tokens=_md.parse(source)
        for token in tokens:
            for child in token.children or []:
                if child.type!='link_open':continue
                href=child.attrGet('href') or ''
                parsed=urlsplit(href)
                if parsed.scheme or parsed.netloc or not parsed.path:continue
                destination=(path.parent/unquote(parsed.path)).resolve()
                if destination in allowed_files():
                    target='/api/course/files?'+urlencode({'path':destination.relative_to(PROJECT_ROOT).as_posix()})
                    if parsed.fragment:target+='#'+parsed.fragment
                    child.attrSet('href',target)
        return _md.renderer.render(tokens,_md.options,{})

    def allowed_files():
        paths={PROJECT_ROOT/item[key] for item in entries() for key in ('lesson','assignment','solution','reference','task','project')}
        paths.update(COURSE.glob('*.md'));paths.update((COURSE/'portfolio').glob('*.md'))
        paths.add(COURSE/'projects/README.md')
        return {path.resolve() for path in paths}

    @app.get('/api/course/files',response_class=HTMLResponse)
    def linked_file(path:str):
        target=(PROJECT_ROOT/path).resolve()
        if target not in allowed_files():
            raise HTTPException(404,'课程文件不在公开阅读目录')
        return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(target.stem)+'</title><link rel="stylesheet" href="/assets/course.css"></head><body class="document-page"><main><article><a href="/course">← 返回课程</a>'+render_file(path)+'</article></main></body></html>'

    @app.get('/course')
    def course_page():
        return FileResponse(PROJECT_ROOT/'app/web/course.html')

    @app.get('/api/course')
    def course_manifest():
        lessons=[dict(item,assignment_target=assignment_target(item),project_target=assignment_target(item,'project')) for item in entries()]
        return {'lessons':lessons,'authoring_status':'ready_for_self_study','learner_completion':'Day1-11_only','practice_base':'/','reference_answers_separate':True}

    @app.get('/api/course/{day}/content/{artifact}',response_class=HTMLResponse)
    def content(day:int,artifact:str):
        item=entry(day)
        if artifact not in {'lesson','assignment','solution','reference','warmup','project'}:
            raise HTTPException(404,'课件类型不存在')
        field={'assignment':'task','warmup':'assignment'}.get(artifact,artifact)
        return render_file(item[field])

    @app.get('/api/course/{day}/assessment')
    def assessment(day:int,request:Request):
        person(request);entry(day)
        return assess_day(day)

    @app.post('/api/course/{day}/challenge')
    def challenge(day:int,request:Request):
        value=person(request);entry(day)
        try:
            return issue_challenge(day,value['user_id'])
        except (ValueError,OSError,subprocess.SubprocessError) as error:
            raise HTTPException(422,'挑战领取失败：先在本机Git检出中提交基线；课程镜像不发放本机作业。') from error

    @app.post('/api/course/{day}/check')
    def check(day:int,body:Choice,request:Request):
        person(request);entry(day)
        if body.mode not in {'reference','exercise'}:
            raise HTTPException(422,'只支持reference/exercise')
        from app.course.checks import check_day
        return check_day(day,body.mode)

    @app.get('/api/course/labs/diagnostics')
    def diagnostics(request:Request):
        person(request)
        with connect_database() as c:
            ready=c.execute('SELECT 1 AS ready').fetchone()['ready']==1
        return {'web':'ok','database':'ok' if ready else 'error','model_network':'not_probed','identity_source':'server_session',
                'business_mode':'teaching_data','checkpoint_backend':'SQLite_file','jobs':'single_process_tasks','public_deployment':False}

    @app.post('/api/course/labs/graph/{draft_id}')
    def graph(draft_id:str,body:GraphAction,request:Request):
        value=person(request);owned(draft_id,request)
        if body.action not in {'start','show','confirm','submit'} or body.mode not in {'reference','exercise'}:
            raise HTTPException(422,'未知模式或动作')
        if body.action in {'confirm','submit'} and (type(body.revision) is not int or body.revision<1):
            raise HTTPException(422,'确认与提交必须指定用户查看的版本')
        with connect_database() as c:
            row=c.execute('SELECT mode FROM leave_workflow_lab.web_graph_runs WHERE run_id=%s AND draft_id=%s AND user_id=%s',(run_id,draft_id,value['user_id'])).fetchone()
            if row and row['mode']!=body.mode:
                raise HTTPException(409,'此草稿已经绑定另一种模式，请用新草稿比较')
            c.execute('INSERT INTO leave_workflow_lab.web_graph_runs(run_id,draft_id,user_id,mode) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',(run_id,draft_id,value['user_id'],body.mode))
        try:
            return graph_operation(run_id,draft_id,TrustedAccessContext(value['user_id'],(),()),body.mode,body.action,body.revision)
        except NotImplementedError as error:
            raise HTTPException(501,'学习者路由尚未实现；可切换到一份新草稿运行参考模式') from error
        except ValueError as error:
            raise HTTPException(409,str(error)) from error

    @app.get('/api/course/labs/memory')
    def get_memory(request:Request):
        value=person(request);return preference(run_id,value['user_id'])

    @app.post('/api/course/labs/memory')
    def set_memory(body:PreferenceRequest,request:Request):
        value=person(request)
        try:
            return preference(run_id,value['user_id'],body.tone,body.delete)
        except ValueError as error:
            raise HTTPException(422,str(error)) from error

    @app.post('/api/course/labs/context')
    def context(body:ContextRequest,request:Request):
        value=person(request)
        with connect_database() as c:
            balance=account_balance(c,run_id,value['user_id'])
        facts={'current_user':value['username'],'balance':balance,'preference':preference(run_id,value['user_id'])}
        try:
            return select_context(facts,[x.model_dump() for x in body.turns],body.question,body.budget_chars)
        except ValueError as error:
            raise HTTPException(422,str(error)) from error

    @app.post('/api/course/labs/mcp')
    def mcp(request:Request):
        value=person(request);return mcp_client(value['username'],2026,run_id)

    @app.post('/api/course/labs/skill')
    def skill(request:Request):
        value=person(request);return execute_report(run_id,value['user_id'])

    @app.post('/api/course/labs/bi')
    def bi(body:BIRequest,request:Request):
        value=person(request)
        query=body.sql;call=None
        if not query:
            call={'purpose':'chatbi_sql','prompt_version':'course-chatbi-v1'}
            with model_guard:
                raw=tracked_model_call(sql_messages(body.question),call,prompt_version='course-chatbi-v1')
            try:
                plan=SqlPlan.model_validate_json(raw)
            except ValueError as error:
                raise HTTPException(502,'模型SQL方案未通过结构校验') from error
            if plan.clarification:
                return {'clarification':plan.clarification,'executed':False,'model_call':call}
            query=plan.sql
        try:
            result=execute_query(query,value['department'])
        except ValueError as error:
            raise HTTPException(422,str(error)) from error
        except (UndefinedColumn,UndefinedTable,SQLSyntaxError,DivisionByZero) as error:
            raise HTTPException(422,'查询无法执行，请核对字段、别名、计算和过滤口径') from error
        except (QueryCanceled,InsufficientPrivilege) as error:
            raise HTTPException(422,'查询被数据库资源或权限策略阻止') from error
        result.update(model_call=call,executed=True)
        return result

    @app.post('/api/course/labs/agent')
    def agent(body:AgentRequest,request:Request):
        from app.course.bounded_agent import run_agent
        value=person(request)
        return run_agent(body.question,run_id,value['user_id'])

    @app.post('/api/course/labs/policy')
    def policy(body:AgentRequest,request:Request):
        from app.course.policy_lab import run_policy
        value=person(request)
        try:
            return run_policy(body.question,value['username'],value['department'],model_guard)
        except RuntimeError as error:
            raise HTTPException(503,'本机授权RAG环境尚未就绪：需要既有Embedding依赖与模型；轻量课程镜像不包含这些权重。') from error

    @app.get('/api/course/labs/traces')
    def trace_list(request:Request):
        value=person(request)
        return [row for row in traces if row['user_id']==value['user_id']][-30:]

    @app.post('/api/course/labs/jobs')
    async def new_job(request:Request):
        value=await asyncio.to_thread(person,request)
        try:
            return await jobs.start_job(run_id,value['user_id'])
        except ValueError as error:
            raise HTTPException(429,str(error)) from error

    @app.get('/api/course/labs/jobs/{job_id}')
    def job_state(job_id:str,request:Request):
        value=person(request)
        try:
            return jobs.owned_job(job_id,run_id,value['user_id'])
        except PermissionError as error:
            raise HTTPException(404,'作业不存在') from error

    @app.post('/api/course/labs/jobs/{job_id}/cancel')
    def stop_job(job_id:str,request:Request):
        value=person(request)
        try:
            return jobs.cancel_job(job_id,run_id,value['user_id'])
        except PermissionError as error:
            raise HTTPException(404,'作业不存在') from error

    @app.get('/api/course/labs/jobs/{job_id}/events')
    async def stream(job_id:str,request:Request,after:int=0):
        value=await asyncio.to_thread(person,request)
        try:
            await asyncio.to_thread(jobs.owned_job,job_id,run_id,value['user_id'])
        except PermissionError as error:
            raise HTTPException(404,'作业不存在') from error
        try:
            cursor=max(after,int(request.headers.get('last-event-id','0')))
            if cursor<0: raise ValueError()
        except ValueError as error:
            raise HTTPException(422,'事件序号无效') from error
        return StreamingResponse(jobs.event_stream(request,job_id,run_id,value['user_id'],cursor),media_type='text/event-stream',headers={'X-Accel-Buffering':'no','Cache-Control':'no-cache'})

    @app.post('/api/course/labs/training')
    def train(request:Request):
        person(request)
        if not _training_gate.acquire(blocking=False):
            raise HTTPException(409,'已有CPU训练进行中')
        try:
            code="import json; from scripts.train_tiny_lora import run; print(json.dumps(run(60)[0]))"
            result=subprocess.run([sys.executable,'-X','utf8','-c',code],cwd=PROJECT_ROOT,capture_output=True,text=True,encoding='utf-8',timeout=180)
            if result.returncode:
                raise HTTPException(503,'CPU训练失败，请检查requirements-training.txt依赖和本机日志')
            return json.loads(result.stdout)
        finally:
            _training_gate.release()
