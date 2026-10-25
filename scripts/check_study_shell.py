"""Verify the independent HTTP shell with disposable accounts, not learner workflows."""
from datetime import datetime
import json
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from app.leave_web import create_app
from app.pgvector_store import PROJECT_ROOT, connect_database
from course.projects import study_app
from course.projects.study_routes import router


def main():
    run_id='day12-web-check-'+uuid4().hex
    report={'kind':'author_http_shell_validation','learner_workflow_completed':False,'checks':[],'cleaned':False}
    origin={'Origin':'http://testserver'}
    try:
        application=create_app(run_id,write_reports=False);application.include_router(router)
        with patch.object(study_app,'RUN_ID',run_id),TestClient(application) as client:
            assert client.get('/api/independent/context').status_code==401
            for username,department,days in [('zhangsan','研发部',9),('lisi','财务部',3),('wangwu','运营部',0),('zhaoliu','产品部',15)]:
                assert client.post('/api/login',headers=origin,json={'username':username,'password':'demo123'}).status_code==200
                value=client.get('/api/independent/context').json()
                assert value['run_id']==run_id and value['username']==username and value['department']==department
                assert value['independent_workflow_implemented'] is False
                response=client.get('/api/me').json()
                # Account balance schema is produced by the existing app; read the actual available value.
                assert response['balance']['remaining_days']==days,response
            report['checks'].append('Four real SQL teaching accounts, session-derived identity and initial balance in an isolated run; independent workflow honestly remains unwired')
            client.post('/api/logout',headers=origin,json={})
            assert client.get('/api/independent/context').status_code==401
            report['status']='passed'
    finally:
        with connect_database() as connection:
            connection.execute('DELETE FROM leave_workflow_lab.runs WHERE id=%s',(run_id,))
            report['cleaned']=connection.execute('SELECT count(*) AS n FROM leave_workflow_lab.runs WHERE id=%s',(run_id,)).fetchone()['n']==0
        path=PROJECT_ROOT/'reports'/f"course-study-shell-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2));print(path)


if __name__=='__main__':main()
