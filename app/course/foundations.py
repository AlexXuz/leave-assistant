"""Small offline foundation contracts; independent project review stays separate."""
from copy import deepcopy
import importlib
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

from app.paths import PROJECT_ROOT


MODULES={1:'exercises',2:'exercises',3:'policy_qa',4:'retrieval',5:'langchain_rag',
         6:'hybrid_retrieval',7:'document_sync',8:'pdf_ingestion',9:'docx_ingestion',
         10:'office_tools',11:'leave_submission'}


def check_foundation(day,mode):
    completed=[]
    def load(name):
        path=('app.course.examples.foundations.' if mode=='reference' else 'app.')+name
        module=importlib.import_module(path)
        return module if mode=='reference' else importlib.reload(module)
    def reject(call,error=ValueError):
        try:call()
        except NotImplementedError:raise
        except error:return
        raise AssertionError('应拒绝的输入被放行')
    try:
        module=load(MODULES[day])
        payload={'leaveType':'ANNUAL','startDate':'2026-11-02','endDate':'2026-11-03','reason':'教学案例'}
        if day==1:
            messages=module.build_messages('11月2日至3日请年假','2026-10-25T09:00:00+08:00')
            assert [m['role'] for m in messages]==['system','user']
            raw=json.dumps(payload,ensure_ascii=False)
            assert module.parse_model_output(raw)['startDate']=='2026-11-02'
            response=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=raw))],usage=None)
            with patch.dict(os.environ,{'LLM_API_KEY':'offline-fixture','LLM_MODEL':'offline-fixture','LLM_BASE_URL':'https://example.invalid/v1'}),patch.object(module,'OpenAI') as sdk:
                sdk.return_value.chat.completions.create.return_value=response
                assert module.call_model(messages)==raw
            completed.append('消息/响应/内容/对象分层；固定客户端，不调用真实模型')
        elif day==2:
            draft=module.LeaveExtraction.model_validate(payload);module.validate_date_range(draft)
            invalid=module.LeaveExtraction.model_validate({**payload,'endDate':'2026-11-01'})
            reject(lambda:module.validate_date_range(invalid))
            value=module.parse_model_output(json.dumps({**payload,'reason':None}))
            assert value['missingFields']==['reason']
            completed.append('日期关系与服务端缺失字段，不信任模型声明')
        elif day==3:
            docs=[{'id':'policy-1','content':'超过三天需共同审批。'}];before=deepcopy(docs)
            messages=module.build_policy_messages('连续四天谁审批？',docs)
            assert [m['role'] for m in messages]==['system','user']
            assert 'policy-1' in messages[1]['content'] and docs[0]['content'] in messages[1]['content'] and docs==before
            completed.append('规则与问题/文档分开，ID与正文对应且输入不变')
        elif day==4:
            import numpy as np
            doc={'id':'p','title':'制度','version':'v1','content':'# 制度\n## 审批\n超过三天共同审批。\n## 时间\n提前申请。'}
            chunks=module.split_policy_document(doc)
            assert [c['heading'] for c in chunks]==['审批','时间']
            hits=module.rank_chunks(np.array([1.,0.]),np.array([[0.,1.],[1.,0.]]),chunks,1)
            assert hits[0]['chunk']['id']==chunks[1]['id'] and isinstance(hits[0]['score'],float)
            completed.append('按章切分与向量/片段对应，不加载Embedding权重')
        elif day==5:
            chunk={'id':'p:v1:1','document_id':'p','title':'制度','version':'v1','heading':'审批','content':'共同审批'}
            hits=[{'chunk':chunk,'score':0.5}]
            with patch.object(module,'retrieve_pgvector',return_value=hits) as retrieve:
                chain=module.build_prepare_chain();assert not retrieve.called
                value=chain.invoke({'question':'谁审批？','top_k':1})
                assert value['lc_documents'][0].id==chunk['id'] and value['documents'][0]['content']==chunk['content']
            completed.append('惰性链构建、Document映射与invoke时执行；检索为固定替身')
        elif day==6:
            a={'id':'a'};b={'id':'b'}
            rankings=[[{'chunk':a,'score':9.},{'chunk':b,'score':8.}],[{'chunk':b,'score':0.1}]]
            before=deepcopy(rankings);fused=module.fuse_rrf(rankings,2,60)
            assert fused[0]['chunk']['id']=='b' and rankings==before
            reject(lambda:module.fuse_rrf([],0,60))
            completed.append('融合按排名和ID，原路分数不直接相加')
        elif day==7:
            assert module.plan_document_sync([],[],complete_snapshot=True)==[]
            reject(lambda:module.plan_document_sync([],[],complete_snapshot=False))
            completed.append('只有完整快照才允许推断删除；真实事务与权限另需独立证据')
        elif day==8:
            pages=module.read_pdf_pages(PROJECT_ROOT/'data/ingestion_lab/travel-policy.pdf')
            assert len(pages)==2 and pages[0]['page']==1 and pages[0]['text'].strip()
            completed.append('实际PDF文本与物理页码；未将扫描件置信度当正确率')
        elif day==9:
            blocks=module.read_docx_blocks(PROJECT_ROOT/'data/ingestion_lab/travel-policy.docx')
            assert len(blocks)==11 and [b['block'] for b in blocks]==list(range(1,12))
            assert sum(b['kind']=='table' for b in blocks)==2
            completed.append('实际Word正文/表格交错读取，未伪造页码')
        elif day==10:
            from app.permission_service import TrustedAccessContext
            class Service:
                def get_balance(self,user_id,year):return {'status':'not_found','year':year,'remaining_days':None,'user':user_id}
            identity=TrustedAccessContext('fixture-user',(),())
            result=module.execute_office_tool('get_my_leave_balance','{"year":2026}',identity,'fixture-source',Service())
            assert result['status']=='not_found' and result['remaining_days'] is None and result['user']=='fixture-user'
            reject(lambda:module.execute_office_tool('unknown','{}',identity,'fixture-source',Service()))
            completed.append('白名单调度与可信身份，not_found不等于0')
        elif day==11:
            from app.permission_service import TrustedAccessContext
            identity=TrustedAccessContext('fixture-user',(),())
            reject(lambda:module.submit_leave('draft',True,'key',identity,None))
            reject(lambda:module.submit_leave('draft',1,'key',None,None),PermissionError)
            confirm=load('leave_confirmation')
            from app.leave_confirmation_store import TeachingConfirmationStore,teaching_draft
            row=teaching_draft();identity=TrustedAccessContext(row['user_id'],(),())
            store=TeachingConfirmationStore([row])
            first=confirm.confirm_leave_draft(row['draft_id'],1,identity,store)
            assert confirm.confirm_leave_draft(row['draft_id'],1,identity,store)==first and store.confirm_write_count==1
            completed.append('版本/身份拒绝及内存确认幂等；不冒称真实SQL提交通过')
        return {'day':day,'mode':mode,'status':'passed','checks_passed':completed,'scope':'offline_warmup_contracts_not_independent_completion'}
    except NotImplementedError:
        return {'day':day,'mode':mode,'status':'not_implemented','checks_passed':completed}
    except ImportError as error:
        return {'day':day,'mode':mode,'status':'setup_required','checks_passed':completed,'message':str(error)}
    except Exception as error:
        return {'day':day,'mode':mode,'status':'failed','checks_passed':completed,'error_type':type(error).__name__,'message':str(error)}
