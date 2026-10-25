"""独立Compose课程环境冒烟；保留一份可重试的演示申请，不消耗本机8012账户。"""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import httpx
from app.pgvector_store import PROJECT_ROOT


def main():
    docker=shutil.which('docker') or str(Path(os.environ['LOCALAPPDATA'])/'Programs/DockerDesktop/resources/bin/docker.exe')
    base=[docker,'compose','--env-file','.env.pgvector','-f','deployment/compose.course.yaml']
    marker='course-container-smoke-v1'
    seed='''import json
from app.leave_web_accounts import WEB_RUN_ID,initialize_accounts,create_account_draft,web_view
from app.pgvector_store import connect_database
from app.permission_service import TrustedAccessContext
from app.exercises import LeaveExtraction
with connect_database() as c:
 initialize_accounts(c,WEB_RUN_ID)
 access=TrustedAccessContext('web-zhangsan',(),())
 row=c.execute("SELECT draft_id FROM leave_workflow_lab.drafts WHERE run_id=%s AND user_id=%s AND payload->>'reason'=%s",(WEB_RUN_ID,access.user_id,'course-container-smoke-v1')).fetchone()
 if row: view=web_view(c,WEB_RUN_ID,row['draft_id'],access)
 else: view=create_account_draft(c,WEB_RUN_ID,access,LeaveExtraction.model_validate({'leaveType':'ANNUAL','startDate':'2026-11-02','endDate':'2026-11-05','reason':'course-container-smoke-v1'}))
 print(json.dumps(view,ensure_ascii=False))
'''
    record={'environment':'independent_leave_course_compose_port_8013','model_called':False,'checks':[],'fixture_retained':True,'main_host_accounts_touched':False}
    with httpx.Client(base_url='http://127.0.0.1:8013',trust_env=False,timeout=35) as client:
        origin={'Origin':'http://127.0.0.1:8013'}
        client.post('/api/login',headers=origin,json={'username':'zhangsan','password':'demo123'}).raise_for_status()
        try:
            seeded=subprocess.run(base+['exec','-T','web','python','-X','utf8','-'],input=seed,cwd=PROJECT_ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
            draft=json.loads(seeded.stdout);endpoint='/api/course/labs/graph/'+draft['draft_id']
            def act(action):
                r=client.post(endpoint,headers=origin,json={'mode':'reference','action':action,'revision':1});r.raise_for_status();return r.json()
            before=act('start')
            subprocess.run(base+['restart','web'],cwd=PROJECT_ROOT,capture_output=True,text=True,check=True)
            for _ in range(40):
                try:
                    if client.get('/health',timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.5)
            restored=act('show');assert restored['interrupts']==before['interrupts']
            record['checks'].append('Container restart retains login session, business draft and actual SQLite graph interrupt')
            if restored['interrupts'] and restored['interrupts'][0]['action']=='confirm':restored=act('confirm')
            if restored['interrupts'] and restored['interrupts'][0]['action']=='submit':restored=act('submit')
            assert restored['business_state']['application']['status']=='PENDING_APPROVAL'
            replay=act('submit');assert replay['business_state']['application']==restored['business_state']['application']
            record['checks'].append('Reference graph explicit confirm and submit create one pending-approval application; replay keeps ID')
            for lab in ('mcp','skill'):
                result=client.post('/api/course/labs/'+lab,headers=origin,json={});result.raise_for_status()
            bi=client.post('/api/course/labs/bi',headers=origin,json={'sql':"SELECT department,SUM(days) AS total_days FROM course_bi.visible_leave WHERE month='2026-10' AND status='APPROVED' GROUP BY department"})
            bi.raise_for_status();assert bi.json()['rows']==[{'department':'研发部','total_days':6}]
            assert len(client.get('/api/course').json()['lessons'])==26
            record['checks'].append('Linux container MCP child, Skill subprocess and authorized SQL role execute successfully; course has 26 lessons')
            record['application']=restored['business_state']['application'];record['status']='passed'
            record['image_id']=subprocess.run([docker,'image','inspect','--format','{{.Id}}','leave-course-web:latest'],capture_output=True,text=True,check=True).stdout.strip()
        finally:client.post('/api/logout',headers=origin,json={})
    path=PROJECT_ROOT/'reports'/f"course-container-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(record,ensure_ascii=False,indent=2));print(path)


if __name__=='__main__':main()
