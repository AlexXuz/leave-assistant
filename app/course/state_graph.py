"""真实StateGraph + SQLite检查点。业务事实/授权仍取PostgreSQL。"""
from pathlib import Path
from typing import TypedDict
from threading import RLock
import hashlib

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

from app.course.examples.foundations.leave_confirmation import confirm_leave_draft
from app.course.examples.foundations.leave_submission import submit_leave
from app.leave_web_accounts import web_view
from app.leave_workflow_store import PostgresLeaveStore
from app.pgvector_store import PROJECT_ROOT, connect_database
from app.course.examples.leave_graph_routing import route_leave_workflow as reference_route

_lock=RLock()  # 本机单进程；SQL幂等/锁仍负责业务写入的最终正确性。


class State(TypedDict, total=False):
    draft_status: str
    missing_fields: list[str]
    application_id: str | None
    revision: int
    view: dict


def graph_operation(run_id, draft_id, access, mode='reference', action='start', revision=None, checkpoint_file: Path | None=None):
    def load():
        with connect_database() as c:
            return web_view(c,run_id,draft_id,access)
    def update(view):
        return {'view':view,'draft_status':view['draft_status'],'missing_fields':view['missing_fields'],
                'application_id':view['application']['application_id'] if view['application'] else None,'revision':view['revision']}
    def inspect(state):
        return update(load())
    def route(state):
        if mode=='reference':
            result=reference_route(state)
        else:
            import importlib
            from app import leave_graph_routing
            result=importlib.reload(leave_graph_routing).route_leave_workflow(state)
        return 'wait_submit' if result=='submit' else result
    def wait_confirmation(state):
        fresh=load()
        decision=interrupt({'action':'confirm','revision':fresh['revision'],'draft':fresh['draft']})
        if decision!={'action':'confirm','revision':fresh['revision']}:
            raise ValueError('确认动作或版本不匹配')
        with connect_database() as c:
            confirm_leave_draft(draft_id,decision['revision'],access,PostgresLeaveStore(c,run_id))
        return update(load())
    def wait_submit(state):
        fresh=load()
        decision=interrupt({'action':'submit','revision':fresh['revision']})
        if decision!={'action':'submit','revision':fresh['revision']}:
            raise ValueError('提交动作或版本不匹配')
        return update(fresh)
    def submit(state):
        with connect_database() as c:
            request=c.execute('SELECT request_key FROM leave_workflow_lab.web_draft_requests WHERE run_id=%s AND draft_id=%s AND user_id=%s',(run_id,draft_id,access.user_id)).fetchone()
            if not request:
                raise PermissionError('申请不属于当前用户')
            submit_leave(draft_id,state['revision'],request['request_key'],access,PostgresLeaveStore(c,run_id))
        return update(load())
    builder=StateGraph(State)
    for name,node in [('inspect',inspect),('wait_confirmation',wait_confirmation),('wait_submit',wait_submit),('submit',submit)]:
        builder.add_node(name,node)
    for name in ('request_details','explain_block','show_result'):
        builder.add_node(name,lambda state: {})
        builder.add_edge(name,END)
    builder.add_edge(START,'inspect')
    builder.add_conditional_edges('inspect',route,{k:k for k in ('request_details','explain_block','show_result','wait_confirmation','wait_submit')})
    builder.add_edge('wait_confirmation','wait_submit')
    builder.add_edge('wait_submit','submit')
    builder.add_edge('submit','show_result')
    path=checkpoint_file or PROJECT_ROOT/'tmp/course/checkpoints.sqlite3'
    path.parent.mkdir(parents=True,exist_ok=True)
    # 不接受浏览器提供thread_id，检查点线程按服务端身份和草稿派生。
    thread=hashlib.sha256(f'{run_id}:{access.user_id}:{draft_id}'.encode()).hexdigest()
    config={'configurable':{'thread_id':thread},'recursion_limit':12}
    with _lock, SqliteSaver.from_conn_string(str(path)) as saver:
        graph=builder.compile(checkpointer=saver)
        fresh=load()  # 读取前先确认本人归属，检查点不提供授权。
        snapshot=graph.get_state(config)
        if action=='start' and not snapshot.values:
            graph.invoke({},config)
        elif action in ('confirm','submit'):
            if revision!=fresh['revision'] or type(revision) is not int:
                raise ValueError('操作必须绑定用户看到的当前版本')
            waiting=[i.value for task in snapshot.tasks for i in task.interrupts]
            if waiting:
                if waiting[0]['action']!=action:
                    raise ValueError('动作不对应当前暂停点')
                graph.invoke(Command(resume={'action':action,'revision':revision}),config)
            elif snapshot.next==('submit',) and action=='submit':
                graph.invoke(None,config)  # 失败节点重试，仍复用SQL请求key。
            elif fresh['application'] and action=='submit':
                pass  # 完成后重复点击展示原申请，不自动启动新图。
            else:
                raise ValueError('当前没有可恢复的对应暂停点')
        elif action not in ('start','show'):
            raise ValueError('未知图动作')
        snapshot=graph.get_state(config)
        waiting=[i.value for task in snapshot.tasks for i in task.interrupts]
        return {'engine':'LangGraph','mode':mode,'next':list(snapshot.next),'interrupts':waiting,
                'business_state':load(),'persistent_checkpoint':True,'thread_id_source':'server_owned_draft'}
