"""Validate the course rules with disposable fixtures, never complete a learner task."""
from copy import deepcopy
import asyncio
from datetime import datetime
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from app.course import assessment
from app.course import jobs as report_jobs
from app.course.checks import check_day
from app.pgvector_store import PROJECT_ROOT


def main():
    report={'kind':'author_rule_validation','learner_completed':False,'checks':[]}
    manifest=json.loads((PROJECT_ROOT/'course/manifest.json').read_text(encoding='utf-8'))
    items=manifest['lessons']
    assert [x['day'] for x in items]==list(range(1,27))
    assert [x['day'] for x in items if x['hard_gate']]==[19,24,26]
    before={item['submission']:assessment.digest(PROJECT_ROOT/item['submission']) for item in items}
    for item in items:
        for key in ('lesson','assignment','project','solution','reference','task','submission'):
            assert (PROJECT_ROOT/item[key]).is_file(),item[key]
        assert item['solution'].endswith('.md')
        task=(PROJECT_ROOT/item['task']).read_text(encoding='utf-8')
        lesson=(PROJECT_ROOT/item['lesson']).read_text(encoding='utf-8')
        assert all(x in task for x in ('公开变体','失败','验收标准','生产边界'))
        assert '生产还差什么，以及下一步' in lesson
        warmup=check_day(item['day'],'reference')
        assert warmup['status'] in {'passed','manual_review_required'}
        assert warmup['completion_eligible'] is False
        record=json.loads((PROJECT_ROOT/item['submission']).read_text(encoding='utf-8'))
        if record.get('status')=='not_started':
            assert assessment.assess_day(item['day'])['completion_eligible'] is False
    report['checks'].append('26 task files, separate hints/examples, concrete boundaries and non-completing author/warmup checks')
    artifact_root=PROJECT_ROOT/'course/learner_artifacts';artifact_root.mkdir(exist_ok=True)
    issued_root=PROJECT_ROOT/'course/challenges/issued';issued_root.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='rule-fixture-',dir=artifact_root) as artifacts, TemporaryDirectory(prefix='rule-fixture-',dir=issued_root) as issued:
        # Synthetic accepted records test bookkeeping only; they never enter submissions.
        day=12;commit='a'*40;identifier='challenge-'+uuid4().hex
        challenge=Path(issued)/'case.json'
        challenge.write_text(json.dumps({'id':identifier,'day':day,'baseline_commit':'b'*40}),encoding='utf-8')
        record=deepcopy(json.loads((PROJECT_ROOT/assessment.lesson(day)['submission']).read_text(encoding='utf-8')))
        record.update(status='submitted',implementation_commit=commit,challenge_file=challenge.relative_to(PROJECT_ROOT).as_posix(),
                      challenge_sha256=assessment.digest(challenge),independent_before_reference=True,
                      design_notes='Synthetic rule fixture, not learner evidence.',reproduction_steps=['fixture setup','fixture evaluation'])
        for kind in ('normal','variant','failure_recovery'):
            path=Path(artifacts)/(kind+'.json')
            payload={'producer':'learner','day':day,'kind':kind,'implementation_commit':commit,'challenge_id':identifier,
                     'environment':{'fixture_only':True},'input':{},'expected':{},'actual':{},'passed':True,'run_at':'fixture',
                     'failure_observed':'synthetic failure','recovery_observed':'synthetic recovery'}
            path.write_text(json.dumps(payload),encoding='utf-8')
            record['artifacts'].append({'kind':kind,'path':path.relative_to(PROJECT_ROOT).as_posix(),'sha256':assessment.digest(path)})
        assert assessment.evaluate_record(day,record)['status']=='pending_review'
        record['review'].update(status='accepted',reviewer='synthetic fixture',reviewed_at='fixture',notes='Tests record handling only.',
                                novel_requirement_confirmed=True,critical_checks={f'D12-C{i}':True for i in (1,2,3)})
        assert assessment.evaluate_record(day,record)['completion_eligible'] is True
        for mutation in ('tampered_hash','author_report','duplicate_artifact','no_novelty','critical_failure','violation','no_review'):
            value=deepcopy(record)
            if mutation=='tampered_hash':value['artifacts'][0]['sha256']='0'*64
            elif mutation=='author_report':value['producer']='author'
            elif mutation=='duplicate_artifact':value['artifacts'][1]=value['artifacts'][0]
            elif mutation=='no_novelty':value['review']['novel_requirement_confirmed']=False
            elif mutation=='critical_failure':value['review']['critical_checks']['D12-C2']=False
            elif mutation=='violation':value['review']['critical_violations']=['unauthorized write']
            else:value['review']['status']='pending'
            assert not assessment.evaluate_record(day,value)['completion_eligible'],mutation
        try:assessment.scoped_path('.env',['course/learner_artifacts'])
        except ValueError:pass
        else:raise AssertionError('Evidence path escape accepted')
    report['checks'].append('Synthetic rule fixtures reject tampering, copied author reports, duplicate artifacts, unreviewed novelty and every critical failure; no real completion written')
    # Exercise actual gate calculation while independently controlling review outcomes.
    def reviewed_except(missing):
        return lambda day,record:{'day':day,'status':'accepted_by_recorded_review','completion_eligible':day not in missing,'hard_gate':day in assessment.GATES,'issues':[]}
    for target,missing,expected in ((19,{13},13),(20,{19},19),(24,{22},22),(25,{24},24),(26,{25},25)):
        with patch.object(assessment,'evaluate_record',side_effect=reviewed_except(missing)):
            value=assessment.assess_day(target)
            assert not value['completion_eligible'] and expected in value['blocked_by_days'],value
    report['checks'].append('Day19/24/26 gates and downstream completion blocked by missing prerequisite reviews; reading remains unrestricted')
    jobs=[{'source_url':f'https://example.invalid/fixture/{i}','captured_at':'fixture','role_family':'fixture','primary':i==0,
           'requirements':[{'requirement':'fixture requirement','priority':'must' if i==0 else 'nice',
                            'evidence':'fixture' if i==0 else None,'gap_status':'closed' if i==0 else 'open','gap_plan':'fixture plan'}]} for i in range(5)]
    issues=[];assessment.validate_jobs(jobs,issues);assert not issues
    jobs[0]['requirements'][0]['gap_status']='open'
    issues=[];assessment.validate_jobs(jobs,issues);assert issues
    issues=[];assessment.validate_jobs(jobs[:4],issues);assert issues
    report['checks'].append('Day25 five-to-ten job mapping and primary must-have evidence required; nice-to-have plans remain allowed')
    # Reproduce a worker committing between an empty event read and terminal-state
    # observation. The old events-first loop returned without delivering done.
    observed={'terminal':False}
    def terminal(*args):
        observed['terminal']=True
        return {'status':'completed'}
    def final_events(job_id,after):
        if observed['terminal'] and after==0:
            return [{'seq':1,'event':'done','payload':{'fixture_only':True}}]
        return []
    class Connected:
        async def is_disconnected(self):return False
    async def frames():
        return [frame async for frame in report_jobs.event_stream(Connected(),'job','run','user',0)]
    with patch.object(report_jobs,'owned_job',side_effect=terminal),patch.object(report_jobs,'read_events',side_effect=final_events):
        streamed=asyncio.run(frames())
    assert len(streamed)==1 and 'event: done' in streamed[0] and 'id: 1' in streamed[0]
    report['checks'].append('Deterministic SSE terminal-commit race: final persisted event delivered exactly once before stream closes')
    assert before=={item['submission']:assessment.digest(PROJECT_ROOT/item['submission']) for item in items}
    report.update(status='passed',all_learner_submissions_unchanged=True)
    path=PROJECT_ROOT/'reports'/f"course-revision-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));print(path)


if __name__=='__main__':main()
