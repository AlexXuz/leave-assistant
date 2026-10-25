"""助教检查：真实PostgreSQL演示账号/共享额度，模型固定响应；结束只清理本检查run。"""
from datetime import datetime
import json
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.leave_web import COOKIE, create_app
from app.pgvector_store import PROJECT_ROOT, connect_database


def main():
    run_id = 'day12-web-check-' + uuid4().hex
    record = {'run_id':run_id,'real_database':True,'chat_model':'fixed_response','checks':[],'cleaned':False}
    origin = {'Origin':'http://testserver'}
    annual = {'leaveType':'ANNUAL','startDate':'2026-11-02','endDate':'2026-11-05','reason':'演示账号检查'}
    web = create_app(run_id,write_reports=False)
    def sign_in(client,username):
        result=client.post('/api/login',headers=origin,json={'username':username,'password':'demo123'})
        assert result.status_code==200
    def make(client,model,payload=annual):
        model.return_value=json.dumps(payload)
        result=client.post('/api/drafts',headers=origin,json={'text':'教学固定提取响应'})
        assert result.status_code==201, result.text
        return result.json()
    def action(client,draft,name):
        return client.post('/api/drafts/'+draft['draft_id']+'/'+name,headers=origin,json={'revision':1})
    try:
        with TestClient(web) as client, patch('app.leave_web.tracked_model_call') as model:
            assert client.get('/').status_code==200
            assert client.get('/assets/app.js').status_code==200
            assert len(client.get('/api/demo-accounts').json()['accounts'])==4
            assert client.get('/api/me').status_code==401
            assert client.post('/api/login',json={'username':'zhangsan','password':'demo123'}).status_code==403
            assert client.post('/api/login',headers=origin,json={'username':'zhangsan','password':'wrong'}).status_code==401
            sign_in(client,'zhangsan')
            assert client.get('/api/me').json()['balance']['remaining_days']==9
            assert client.post('/api/drafts',headers=origin,json={'text':'年假','user_id':'web-zhaoliu'}).status_code==422
            first,second=make(client,model),make(client,model)
            assert first['run_id']==second['run_id']==run_id
            assert action(client,first,'submit').status_code==409
            assert client.post('/api/drafts/'+first['draft_id']+'/confirm',headers=origin,json={'revision':True}).status_code==422
            assert action(client,first,'confirm').status_code==200
            assert action(client,second,'confirm').status_code==200
            before_calls=model.call_count
            submitted=action(client,first,'submit').json()
            assert submitted['application']['status']=='PENDING_APPROVAL'
            assert (submitted['remaining_days'],submitted['reserved_days'],submitted['used_days'])==(5,4,1)
            assert action(client,first,'submit').json()==submitted
            next_result=action(client,second,'submit').json()
            assert (next_result['remaining_days'],next_result['reserved_days'],next_result['used_days'])==(1,8,1)
            assert model.call_count==before_calls
            third=make(client,model)
            assert third['assessment']['code']=='INSUFFICIENT_BALANCE' and third['remaining_days']==1
            assert action(client,third,'confirm').status_code==409
            record['checks'].append('One account shares quota across drafts: 9 -> 5 -> 1; retries never reserve twice; confirmation has no reservation')
            personal=make(client,model,{**annual,'leaveType':'PERSONAL'})
            assert personal['assessment']['code']=='LEAVE_TYPE_UNSUPPORTED'
            assert personal['remaining_days'] is None and personal['reserved_days'] is None
            assert action(client,personal,'confirm').status_code==409
            record['checks'].append('Personal leave explicitly unsupported; annual allowance never presented as personal-leave allowance')
            token=client.cookies.get(COOKIE)
            assert client.post('/api/logout',headers=origin,json={}).status_code==200
            assert client.get('/api/me').status_code==401
            with TestClient(web) as revoked:
                revoked.cookies.set(COOKIE,token)
                assert revoked.get('/api/me').status_code==401
            sign_in(client,'lisi')
            assert client.get('/api/me').json()['balance']['remaining_days']==3
            lisi=make(client,model)
            assert lisi['assessment']['code']=='INSUFFICIENT_BALANCE'
            path='/api/drafts/'+first['draft_id']
            assert client.get(path).status_code==404
            assert client.post(path+'/submit',headers=origin,json={'revision':1}).status_code==404
            assert all(v['user_id']=='web-lisi' for v in client.get('/api/drafts').json())
            sign_in(client,'wangwu')
            assert client.get('/api/me').json()['balance']['remaining_days']==0
            assert make(client,model)['assessment']['code']=='INSUFFICIENT_BALANCE'
            sign_in(client,'zhaoliu')
            assert client.get('/api/me').json()['balance']['remaining_days']==15
            assert make(client,model)['draft_status']=='READY_FOR_CONFIRMATION'
            record['checks'].append('Four logins have independent 9/3/0/15 initial quotas, owned histories; forged identity and cross-account access rejected; logout revokes session')
            # New application instance initializes again but must not reset prior balances.
            with TestClient(create_app(run_id,write_reports=False)) as restarted:
                sign_in(restarted,'zhangsan')
                assert restarted.get('/api/me').json()['balance']['remaining_days']==1
                history=restarted.get('/api/drafts').json()
                assert len(history)==4
                assert sum(bool(v['application']) for v in history)==2
                assert restarted.get(path).json()['application']==submitted['application']
                assert restarted.post(path+'/route-preview',headers=origin,json={}).status_code in (200,501)
            record['checks'].append('Restart and login retain balance, application IDs and histories; learner route remains unfinished')
            with connect_database() as connection:
                count=connection.execute('SELECT count(*) AS n FROM leave_workflow_lab.applications WHERE run_id=%s',(run_id,)).fetchone()['n']
                assert count==2
            record['status']='passed'
    except Exception as error:
        record.update(status='failed',error_type=type(error).__name__)
        raise
    finally:
        with connect_database() as connection:
            connection.execute('DELETE FROM leave_workflow_lab.runs WHERE id=%s',(run_id,))
            record['cleaned']=connection.execute('SELECT count(*) AS n FROM leave_workflow_lab.runs WHERE id=%s',(run_id,)).fetchone()['n']==0
        report=PROJECT_ROOT/'reports'/f"leave-web-accounts-check-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
        report.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(record,ensure_ascii=False,indent=2));print(report)


if __name__=='__main__':
    main()
