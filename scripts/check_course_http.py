"""课程HTTP验收，固定模型响应，随机SQL命名空间；不是实际模型效果评测。"""
from datetime import datetime
import json
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from app.leave_web import create_app
from app.pgvector_store import PROJECT_ROOT, connect_database


def main():
    run_id='day12-web-check-'+uuid4().hex
    report={'run_id':run_id,'model':'fixed_response','real_database':True,'checks':[],'cleaned':False}
    origin={'Origin':'http://testserver'}
    try:
        with TestClient(create_app(run_id,write_reports=False)) as client:
            assert client.get('/course').status_code==200
            manifest=client.get('/api/course').json();assert len(manifest['lessons'])==15
            for item in manifest['lessons']:
                target=item['assignment_target']
                assert target['relative_path']==item['assignment']
                assert target['absolute_path']==str((PROJECT_ROOT/item['assignment']).resolve())
                if item['assignment'].endswith('.py'):
                    assert target['kind']=='python' and target['functions']
                    assert all(f['line']>0 and f['name'] for f in target['functions'])
                else:
                    assert target['kind']=='document'
                for artifact in ('lesson','assignment','solution'):
                    response=client.get(f"/api/course/{item['day']}/content/{artifact}")
                    assert response.status_code==200 and len(response.text)>100
            assert client.get('/api/course/labs/memory').status_code==401
            assert client.post('/api/login',headers=origin,json={'username':'zhangsan','password':'demo123'}).status_code==200
            assert client.post('/api/course/12/check',headers=origin,json={'mode':'reference'}).json()['status']=='passed'
            own=client.post('/api/course/12/check',headers=origin,json={'mode':'exercise'}).json()
            assert own['mode']=='exercise' and own['status'] in {'not_implemented','passed','failed'}
            assert client.post('/api/course/labs/memory',headers=origin,json={'tone':'concise'}).json()['stored']
            assert not client.post('/api/course/labs/memory',headers=origin,json={'delete':True}).json()['stored']
            assert client.post('/api/course/labs/context',headers=origin,json={'question':'当前余额','turns':[],'budget_chars':1600}).status_code==200
            report['checks'].append('15 existing IDE homework targets and callable lines, 45 content pages, explicit reference vs learner modes, authenticated memory/context')
            payload=json.dumps({'leaveType':'ANNUAL','startDate':'2026-11-02','endDate':'2026-11-05','reason':'课程HTTP验收'})
            with patch('app.leave_web.tracked_model_call',return_value=payload):
                draft=client.post('/api/drafts',headers=origin,json={'text':'四天年假'}).json()
            path='/api/course/labs/graph/'+draft['draft_id']
            value=client.post(path,headers=origin,json={'mode':'reference','action':'start'}).json();assert value['interrupts'][0]['action']=='confirm'
            value=client.post(path,headers=origin,json={'mode':'reference','action':'confirm','revision':1}).json();assert value['interrupts'][0]['action']=='submit'
            value=client.post(path,headers=origin,json={'mode':'reference','action':'submit','revision':1}).json();assert value['business_state']['application']
            assert client.post(path,headers=origin,json={'mode':'reference','action':'submit','revision':1}).json()['business_state']['application']==value['business_state']['application']
            report['checks'].append('HTTP graph start/confirm/submit and replay correspond to real persisted business state')
            query="SELECT department,SUM(days) AS total_days FROM course_bi.visible_leave WHERE month='2026-10' AND status='APPROVED' GROUP BY department"
            result=client.post('/api/course/labs/bi',headers=origin,json={'sql':query}).json()
            assert result['rows']==[{'department':'研发部','total_days':6}]
            with patch('app.course.web.tracked_model_call',return_value=json.dumps({'sql':None,'clarification':'请指定月份与状态'})):
                assert client.post('/api/course/labs/bi',headers=origin,json={'question':'请假多少天'}).json()['executed'] is False
            assert client.post('/api/course/labs/bi',headers=origin,json={'sql':'SELECT pg_sleep(1)'}).status_code==422
            report['checks'].append('ChatBI role-scoped result, rejected arbitrary function and clarification without execution')
            job=client.post('/api/course/labs/jobs',headers=origin,json={}).json()
            events=client.get('/api/course/labs/jobs/'+job['id']+'/events')
            assert events.status_code==200 and 'text/event-stream' in events.headers['content-type']
            assert 'event: done' in events.text and 'id: 4' in events.text
            reconnect=client.get('/api/course/labs/jobs/'+job['id']+'/events?after=2')
            assert 'id: 1\n' not in reconnect.text and 'id: 3\n' in reconnect.text
            assert client.get('/api/course/labs/traces').json()
            client.post('/api/login',headers=origin,json={'username':'lisi','password':'demo123'})
            assert client.get('/api/course/labs/jobs/'+job['id']).status_code==404
            assert client.post(path,headers=origin,json={'mode':'reference','action':'show'}).status_code==404
            assert client.get('/api/course/labs/memory').json()['stored'] is False
            report['checks'].append('Actual HTTP SSE framing/cursor and job/graph ownership isolation')
            report['status']='passed'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error))
        raise
    finally:
        with connect_database() as c:
            c.execute('DELETE FROM leave_workflow_lab.runs WHERE id=%s',(run_id,))
            report['cleaned']=c.execute('SELECT count(*) AS n FROM leave_workflow_lab.runs WHERE id=%s',(run_id,)).fetchone()['n']==0
        file=PROJECT_ROOT/'reports'/f"course-http-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        file.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));print(file)


if __name__=='__main__':main()
