"""浏览器自测：同一组输入分别调用作业或参考函数；不自动填答案。"""
from copy import deepcopy
import importlib
import json
from pathlib import Path


def check_day(day: int, mode: str='reference') -> dict:
    result=_check_warmup(day,mode)
    result.update(purpose='author_example' if mode=='reference' else 'warmup_contract',completion_eligible=False)
    return result


def _check_warmup(day: int, mode: str='reference') -> dict:
    if 1<=day<=11:
        from app.course.foundations import check_foundation
        return check_foundation(day,mode)
    if day in (16,25,26):
        return {'day':day,'mode':mode,'status':'manual_review_required','message':'本课按课件的真实操作/证据评分，不用函数断言替代部署或面试。'}
    if mode not in {'reference','exercise'}:
        raise ValueError('只支持reference/exercise')
    manifest=Path(__file__).resolve().parents[2]/'course/manifest.json'
    item=next((item for item in json.loads(manifest.read_text(encoding='utf-8'))['lessons'] if item['day']==day),None)
    if item is None:
        raise ValueError('课程不存在')
    source=item['reference' if mode=='reference' else 'assignment']
    path=Path(source).with_suffix('').as_posix().replace('/','.')
    importlib.invalidate_caches()
    try:
        module=importlib.reload(importlib.import_module(path))  # 保存作业后可直接从页面复验。
    except (SyntaxError,ImportError) as error:
        return {'day':day,'mode':mode,'status':'failed','phase':'import','error_type':type(error).__name__,
                'message':str(error),'line':getattr(error,'lineno',None)}
    passed=[]
    def equal(label,name,args,expected):
        before=deepcopy(args)
        result=getattr(module,name)(*args)
        assert result==expected, f'{label}：结果不符合约定'
        assert args==before, f'{label}：函数修改了输入'
        passed.append(label)
    def rejects(label,name,args):
        try:
            getattr(module,name)(*args)
        except ValueError:
            passed.append(label);return
        raise AssertionError(label+'：应拒绝但被放行')
    try:
        if day==12:
            for status,missing,app,expected in [('READY_FOR_CONFIRMATION',[],None,'wait_confirmation'),('CONFIRMED',[],None,'submit'),('SUBMITTED',[],'application-1','show_result'),('NEEDS_ASSESSMENT',['reason'],None,'request_details'),('BLOCKED',[],None,'explain_block')]:
                equal(status,'route_leave_workflow',[{'draft_status':status,'missing_fields':missing,'application_id':app}],expected)
            rejects('拒绝状态与申请编号矛盾','route_leave_workflow',[{'draft_status':'SUBMITTED','missing_fields':[],'application_id':None}])
        elif day==13:
            fn=module.select_context
            args=[{'remaining_days':3},[{'user':'旧日期'*100,'assistant':'旧回答'*100},{'user':'改为四天','assistant':'等待确认'}],'目前草稿是什么',400]
            before=deepcopy(args);value=fn(*args)
            assert args==before and value['characters']<=400 and value['kept_turns']==1
            assert value['messages'][-1]['content']=='目前草稿是什么' and value['messages'][0]['role']=='system'
            passed.append('保留必要事实/当前问题与完整最新轮次，不超字符预算')
            rejects('必要快照超预算应拒绝','select_context',[{'data':'x'*1000},[],'问题',200])
        elif day==14:
            equal('读取结构化响应','decode_tool_result',[{'isError':False,'structuredContent':{'status':'ok','remaining_days':0}}],{'status':'ok','remaining_days':0})
            equal('读取文本JSON','decode_tool_result',[{'content':[{'type':'text','text':'{"status":"not_found"}'}]}],{'status':'not_found'})
            rejects('不能把工具错误当业务成功','decode_tool_result',[{'isError':True,'structuredContent':{'status':'ok'}}])
        elif day==15:
            metadata=[{'name':'leave-report','description':'部门报告'}]
            equal('只选择唯一技能元数据','select_skill',['leave-report',metadata],{'name':'leave-report','description':'部门报告','load_body':True})
            rejects('拒绝未知路径/技能','select_skill',['../../other',metadata])
        elif day==17:
            equal('事件帧和空行','encode_sse',[1,'stage',{'text':'第一步\n下一行'}],'id: 1\nevent: stage\ndata: {"text": "第一步\\n下一行"}\n\n')
            rejects('事件名不能注入换行','encode_sse',[1,'done\nevent: fake',{}])
            rejects('bool不是序号','encode_sse',[True,'done',{}])
        elif day==18:
            equal('已提交优先','classify_failure',['explain',True,'APITimeoutError'],{'category':'post_commit','action':'read_status_then_retry_same_key','safe_to_claim_not_submitted':False})
            equal('业务拒绝不盲重试','classify_failure',['business',False,'SubmissionBlocked'],{'category':'business_rule','action':'show_reason_no_blind_retry','safe_to_claim_not_submitted':True})
        elif day==19:
            equal('无余额记录不猜0','merge_evidence',[{'status':'not_found'},{'evidence':[{'id':'p1','content':'审批人是主管'}]}],{'balance_status':'not_found','remaining_days':None,'policy_evidence':[{'id':'p1','content':'审批人是主管'}],'allowed_policy_sources':['p1'],'can_submit':False})
            rejects('未知状态拒绝','merge_evidence',[{'status':'maybe'},{}])
        elif day==20:
            equal('检索缺证据不微调','choose_intervention',['missing_candidate'],'fix_retrieval')
            equal('身份/业务错误不微调','choose_intervention',['wrong_live_balance'],'fix_business_tool')
            rejects('场景泄漏拒绝','validate_splits',[[{'scenario_id':'a','split':'train'},{'scenario_id':'a','split':'test'}]])
        elif day==21:
            equal('只监督回答','build_labels',[[1,2,3,0],2,3],[-100,-100,3,-100])
            rejects('没有回答token拒绝','build_labels',[[1,2,0],2,2])
        elif day==22:
            query='SELECT department, SUM(days) AS total_days FROM course_bi.visible_leave GROUP BY department'
            result=module.validate_readonly_sql(query);assert 'LIMIT 100' in result;passed.append('授权单表聚合并限制行数')
            for query in ['SELECT * FROM course_bi.visible_leave','SELECT pg_sleep(1)','DELETE FROM course_bi.leave_facts',"SELECT department FROM course_bi.visible_leave; SELECT 1",'SELECT department FROM course_bi.leave_facts',"SELECT department FROM course_bi.visible_leave UNION SELECT usename FROM pg_user"]:
                rejects('拒绝越界SQL：'+query[:38],'validate_readonly_sql',[query])
        elif day==23:
            equal('图表与SQL行保持一致','chart_spec',[[{'department':'研发部','total_days':6}],'天数','研发部'],{'title':'天数','scope':'研发部','unit':'天','labels':['研发部'],'values':[6],'source':'executed_sql_rows'})
            rejects('不能把bool当数值','chart_spec',[[{'department':'研发部','total_days':True}],'题目','范围'])
        elif day==24:
            equal('部门规则上限','check_department_limit',[5,'研发部',{'研发部':4}],{'allowed':False,'code':'DEPARTMENT_LIMIT_EXCEEDED','limit':4})
            equal('无规则不默认通过','check_department_limit',[1,'未知',{}],{'allowed':False,'code':'POLICY_UNAVAILABLE'})
        else:
            raise ValueError('没有本课的自动检查')
    except NotImplementedError:
        return {'day':day,'mode':mode,'status':'not_implemented','checks_passed':passed}
    except Exception as error:
        return {'day':day,'mode':mode,'status':'failed','checks_passed':passed,'error_type':type(error).__name__,'message':str(error)}
    return {'day':day,'mode':mode,'status':'passed','checks_passed':passed,'scope':'contract_cases_only_not_production_reliability'}
