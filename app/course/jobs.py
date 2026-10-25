"""Day17：单进程异步作业、持久事件、SSE重连与显式取消。不是分布式队列。"""
import asyncio
import json
import time
from uuid import uuid4
from psycopg.types.json import Jsonb
from app.pgvector_store import connect_database
from app.course.reporting import department_report

_tasks={}
_gate=asyncio.Semaphore(4)


def owned_job(job_id,run_id,user_id):
    with connect_database() as c:
        row=c.execute('SELECT id,status,cancel_requested,result,created_at,updated_at FROM leave_workflow_lab.course_jobs WHERE id=%s AND run_id=%s AND user_id=%s',(job_id,run_id,user_id)).fetchone()
    if not row:
        raise PermissionError('作业不存在或不属于当前用户')
    return row


def emit(job_id,event,payload,status=None):
    with connect_database() as c, c.transaction():
        c.execute('SELECT id FROM leave_workflow_lab.course_jobs WHERE id=%s FOR UPDATE',(job_id,))
        seq=c.execute('SELECT coalesce(max(seq),0)+1 AS seq FROM leave_workflow_lab.course_events WHERE job_id=%s',(job_id,)).fetchone()['seq']
        c.execute('INSERT INTO leave_workflow_lab.course_events VALUES(%s,%s,%s,%s)',(job_id,seq,event,Jsonb(payload)))
        c.execute('UPDATE leave_workflow_lab.course_jobs SET updated_at=now() WHERE id=%s',(job_id,))
        if status:
            c.execute('UPDATE leave_workflow_lab.course_jobs SET status=%s,result=%s WHERE id=%s',(status,Jsonb(payload),job_id))


async def worker(job_id,run_id,user_id):
    started=time.monotonic()
    try:
        async with _gate:
            for number,label in enumerate(('读取授权范围','查询部门申请','整理汇总结果'),1):
                row=await asyncio.to_thread(owned_job,job_id,run_id,user_id)
                if row['cancel_requested']:
                    await asyncio.to_thread(emit,job_id,'cancelled',{'message':'任务已取消'},'cancelled')
                    return
                if time.monotonic()-started>20:
                    raise TimeoutError('作业超过总时间预算')
                await asyncio.to_thread(emit,job_id,'stage',{'step':number,'total':3,'message':label})
                await asyncio.sleep(0.7)  # 可见的教学阶段间隔，不伪装成模型token。
            result=await asyncio.to_thread(department_report,run_id,user_id)
            row=await asyncio.to_thread(owned_job,job_id,run_id,user_id)
            if row['cancel_requested']:
                await asyncio.to_thread(emit,job_id,'cancelled',{'message':'结果返回前任务被取消'},'cancelled')
            else:
                await asyncio.to_thread(emit,job_id,'done',result,'completed')
    except asyncio.CancelledError:
        await asyncio.to_thread(emit,job_id,'error',{'error_type':'WorkerStopped'},'failed')
        raise
    except Exception as error:
        await asyncio.to_thread(emit,job_id,'error',{'error_type':type(error).__name__},'failed')
    finally:
        _tasks.pop(job_id,None)


async def start_job(run_id,user_id):
    def create():
        with connect_database() as c, c.transaction():
            c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(run_id+user_id+':jobs',))
            # 上次进程中断留下的任务如实标记失败，不能冒充已恢复。
            c.execute("UPDATE leave_workflow_lab.course_jobs SET status='failed',result='{}'::jsonb WHERE run_id=%s AND user_id=%s AND status='running' AND updated_at<now()-interval '1 minute'",(run_id,user_id))
            count=c.execute("SELECT count(*) AS n FROM leave_workflow_lab.course_jobs WHERE run_id=%s AND user_id=%s AND status='running'",(run_id,user_id)).fetchone()['n']
            if count>=2:
                raise ValueError('每个账号最多两个进行中的作业')
            identifier='job-'+uuid4().hex
            c.execute("INSERT INTO leave_workflow_lab.course_jobs(id,run_id,user_id,status) VALUES(%s,%s,%s,'running')",(identifier,run_id,user_id))
            return identifier
    job_id=await asyncio.to_thread(create)
    _tasks[job_id]=asyncio.create_task(worker(job_id,run_id,user_id))
    return {'id':job_id,'status':'running','event_source':'actual_report_stages_not_llm_tokens'}


def cancel_job(job_id,run_id,user_id):
    owned_job(job_id,run_id,user_id)
    with connect_database() as c:
        c.execute("UPDATE leave_workflow_lab.course_jobs SET cancel_requested=true WHERE id=%s AND run_id=%s AND user_id=%s AND status='running'",(job_id,run_id,user_id))
    return owned_job(job_id,run_id,user_id)


def read_events(job_id,after):
    with connect_database() as c:
        return c.execute('SELECT seq,event,payload FROM leave_workflow_lab.course_events WHERE job_id=%s AND seq>%s ORDER BY seq LIMIT 100',(job_id,after)).fetchall()


async def event_stream(request,job_id,run_id,user_id,after):
    while True:
        if await request.is_disconnected():
            return  # 断开浏览器连接不等于用户取消业务任务。
        events=await asyncio.to_thread(read_events,job_id,after)
        for item in events:
            after=item['seq']
            yield f"id: {after}\nevent: {item['event']}\ndata: {json.dumps(item['payload'],ensure_ascii=False)}\n\n"
        row=await asyncio.to_thread(owned_job,job_id,run_id,user_id)
        if row['status']!='running':
            return
        yield ': heartbeat\n\n'
        await asyncio.sleep(0.4)
