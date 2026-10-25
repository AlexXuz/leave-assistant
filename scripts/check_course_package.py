"""课程包验收：参考函数、真实SQL/检查点/MCP/Skill/SSE；不动学习者演示额度。"""
import asyncio
from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.course.analytics import execute_query
from app.course.checks import check_day
from app.course.memory import preference
from app.course.mcp_client import run_sync
from app.course.skill_runtime import execute_report
from app.course.state_graph import graph_operation
from app.course import jobs
from app.exercises import LeaveExtraction
from app.leave_submission import SubmissionBlocked
from app.leave_web_accounts import initialize_accounts, create_account_draft, account_balance
from app.permission_service import TrustedAccessContext
from app.pgvector_store import PROJECT_ROOT, connect_database


async def check_jobs(run_id,user_id):
    cancelled=await jobs.start_job(run_id,user_id)
    jobs.cancel_job(cancelled['id'],run_id,user_id)
    normal=await jobs.start_job(run_id,user_id)
    for _ in range(30):
        await asyncio.sleep(0.2)
        if jobs.owned_job(normal['id'],run_id,user_id)['status']!='running':break
    assert jobs.owned_job(cancelled['id'],run_id,user_id)['status']=='cancelled'
    assert jobs.owned_job(normal['id'],run_id,user_id)['status']=='completed'
    events=jobs.read_events(normal['id'],0)
    assert [e['event'] for e in events]==['stage','stage','stage','done']
    assert [e['seq'] for e in jobs.read_events(normal['id'],2)]==[3,4]


def main():
    run_id='day12-web-check-'+uuid4().hex
    report={'run_id':run_id,'reference_checks':[],'integrations':[],'cleaned':False,'chat_model_called':False}
    try:
        manifest=json.loads((PROJECT_ROOT/'course/manifest.json').read_text(encoding='utf-8'))
        for item in manifest['lessons']:
            for key in ('lesson','assignment','solution'):
                assert (PROJECT_ROOT/item[key]).is_file(),item[key]
            result=check_day(item['day'],'reference');report['reference_checks'].append(result)
            assert result['status'] in ('passed','manual_review_required'),result
        with connect_database() as c:
            initialize_accounts(c,run_id)
            with c.transaction():c.execute((PROJECT_ROOT/'infra/course_schema.sql').read_text(encoding='utf-8'),prepare=False)
            access=TrustedAccessContext('web-zhangsan',(),())
            draft=create_account_draft(c,run_id,access,LeaveExtraction.model_validate({'leaveType':'ANNUAL','startDate':'2026-11-02','endDate':'2026-11-05','reason':'图检查'}))
        with TemporaryDirectory(dir=PROJECT_ROOT/'tmp') as temp:
            checkpoint=Path(temp)/'checkpoints.sqlite3'
            def graph(action,revision=None):return graph_operation(run_id,draft['draft_id'],access,'reference',action,revision,checkpoint)
            paused=graph('start');assert paused['interrupts'][0]['action']=='confirm'
            assert paused['business_state']['application'] is None
            recovered=graph('show');assert recovered['interrupts']==paused['interrupts']
            confirmed=graph('confirm',1);assert confirmed['interrupts'][0]['action']=='submit'
            assert confirmed['business_state']['reserved_days']==0
            submitted=graph('submit',1);assert submitted['business_state']['application']['status']=='PENDING_APPROVAL'
            retry=graph('submit',1);assert retry['business_state']['application']==submitted['business_state']['application']
        report['integrations'].append('Real StateGraph interrupt, file checkpoint reopening, separate confirm/submit and idempotent replay')
        preference(run_id,access.user_id,'concise')
        assert preference(run_id,'web-lisi')['tone'] is None
        assert preference(run_id,access.user_id,delete=True)['stored'] is False
        report['integrations'].append('User-scoped preference write/read/delete')
        mcp=run_sync('zhangsan',2026,run_id)
        assert mcp['extra_identity_rejected']
        from course.solutions.day14 import decode_tool_result
        assert decode_tool_result(mcp['result'])['status']=='ok'
        report['integrations'].append('Independent MCP stdio process discovery/call and extra identity rejection')
        skill=execute_report(run_id,access.user_id)
        assert skill['data']['application_count']==1 and skill['data']['total_days']==4
        report['integrations'].append('Skill metadata discovery, selected body/reference/template load and real reviewed-script result')
        query="SELECT department,SUM(days) AS total_days FROM course_bi.visible_leave WHERE month='2026-10' AND status='APPROVED' GROUP BY department"
        result=execute_query(query,'研发部')
        assert result['rows']==[{'department':'研发部','total_days':6}]
        assert result['database_role']=='leave_course_bi_reader'
        denied=execute_query("SELECT department,SUM(days) AS total_days FROM course_bi.visible_leave WHERE department='财务部' GROUP BY department",'研发部')
        assert denied['rows']==[]
        with connect_database() as c:
            try:
                with c.transaction():
                    c.execute('SET LOCAL ROLE leave_course_bi_reader')
                    c.execute('SELECT * FROM course_bi.leave_facts')
            except Exception as error:
                assert type(error).__name__=='InsufficientPrivilege'
            else:raise AssertionError('只读角色不应能直接读基表')
        report['integrations'].append('SQL AST guard plus actual no-login read-only DB role, authorized view, hidden other department and denied base table')
        asyncio.run(check_jobs(run_id,access.user_id))
        report['integrations'].append('Real async report task completed/cancelled; persistent events support cursor reconnect')
        report['status']='passed'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error))
        raise
    finally:
        with connect_database() as c:
            c.execute('DELETE FROM leave_workflow_lab.runs WHERE id=%s',(run_id,))
            report['cleaned']=c.execute('SELECT count(*) AS n FROM leave_workflow_lab.runs WHERE id=%s',(run_id,)).fetchone()['n']==0
        path=PROJECT_ROOT/'reports'/f"course-package-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2));print(path)


if __name__=='__main__':main()
