"""Evidence bookkeeping, not an automatic judge of semantic correctness or independence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
from uuid import uuid4

from app.pgvector_store import PROJECT_ROOT
from app.course.profile import read_profile

COURSE=PROJECT_ROOT/'course'
GATES=(19,24,26)
HEX40=re.compile(r'[0-9a-f]{40}')
HEX64=re.compile(r'[0-9a-f]{64}')


def lesson(day):
    items=json.loads((COURSE/'manifest.json').read_text(encoding='utf-8'))['lessons']
    match=next((item for item in items if item['day']==day),None)
    if match is None:
        raise ValueError('课程不存在')
    return match


def catalog(day):
    return json.loads((COURSE/'assessment_catalog.json').read_text(encoding='utf-8'))['lessons'][str(day)]


def read_object(path):
    if path.stat().st_size>1_000_000:
        raise ValueError('证据文件超过1MB，请拆分并保留脱敏结果')
    value=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value,dict):
        raise ValueError('证据必须是JSON对象')
    return value


def scoped_path(relative,roots):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError('证据路径必须相对仓库')
    path=(PROJECT_ROOT/relative).resolve()
    if not path.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError('证据路径不能离开仓库')
    if not any(path.is_relative_to((PROJECT_ROOT/root).resolve()) for root in roots):
        raise ValueError('证据路径超出允许目录')
    if not path.is_file():
        raise ValueError('证据文件不存在')
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def issue_challenge(day,owner='local-learner'):
    item=lesson(day);spec=catalog(day)
    result=subprocess.run(['git','rev-parse','HEAD'],cwd=PROJECT_ROOT,capture_output=True,text=True,timeout=5)
    commit=result.stdout.strip()
    if result.returncode or not HEX40.fullmatch(commit):
        raise ValueError('先在Git检出中提交基线，再领取挑战；轻量容器不用于发放本机作业')
    identifier='challenge-'+uuid4().hex
    value={'schema_version':2,'id':identifier,'day':day,'owner':owner,
           'assessment_version':item.get('assessment_version',2),
           'task_sha256':digest(PROJECT_ROOT/item['task']),
           'issued_at':datetime.now(timezone.utc).isoformat(),
           'baseline_commit':commit,'baseline_project_sha256':digest(PROJECT_ROOT/item['project']),
           'variant':random.SystemRandom().choice(spec['variants']),'failure':spec['failure'],
           'source':'public_task_family','novelty_certified':False,
           'notice':'这是公开任务族抽签，不是秘密留出集；复核者必须确认该需求未被提前练过。',
           'critical_checks':spec['checks']}
    path=COURSE/'challenges/issued'/f'{identifier}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'challenge':value,'challenge_file':path.relative_to(PROJECT_ROOT).as_posix(),
            'challenge_sha256':digest(path),'status':'issued_not_completed'}


def evaluate_record(day,record):
    """Validate hashes/structure and an explicit review record; never run arbitrary report commands."""
    item=lesson(day);issues=[]
    result={'day':day,'hard_gate':item['hard_gate'],'completion_eligible':False,
            'status':'not_started','scope':'artifact_integrity_and_recorded_review_only',
            'message':'热身/作者示范通过不代表本人完成；证据语义与独立性须复核。','issues':issues}
    if record.get('status')=='not_started':
        return result
    if record.get('schema_version')!=2 or record.get('day')!=day or record.get('producer')!='learner':
        issues.append('仅接受本课v2学习者记录，不能复用作者报告')
    assessment_version=item.get('assessment_version',2)
    if assessment_version>=3 and record.get('assessment_version')!=assessment_version:
        issues.append('本课任务已修订，请按当前assessment_version留证；旧OA任务不自动抵新任务')
    commit=record.get('implementation_commit')
    if not isinstance(commit,str) or not HEX40.fullmatch(commit):
        issues.append('缺少40位实现commit')
    if record.get('independent_before_reference') is not True:
        issues.append('须先独立尝试；读过答案的同题请换新需求后再验收')
    if not isinstance(record.get('assistance_used'),list):
        issues.append('须如实列出所用提示/AI/示范，允许空列表')
    if not record.get('design_notes') or not isinstance(record.get('reproduction_steps'),list) or len(record['reproduction_steps'])<2:
        issues.append('缺少本人设计说明或至少两步复现步骤')
    challenge=None
    try:
        path=scoped_path(record.get('challenge_file'),['course/challenges/issued'])
        challenge=read_object(path)
        if record.get('challenge_sha256')!=digest(path):issues.append('挑战文件哈希不匹配')
        if challenge.get('day')!=day or not str(challenge.get('id','')).startswith('challenge-'):
            issues.append('挑战编号/课程不匹配')
        if not HEX40.fullmatch(str(challenge.get('baseline_commit',''))):issues.append('挑战没有有效基线commit')
        if assessment_version>=3:
            if challenge.get('assessment_version')!=assessment_version:
                issues.append('挑战属于旧版任务，请冻结当前任务后重新领取')
            if challenge.get('task_sha256')!=digest(PROJECT_ROOT/item['task']):
                issues.append('任务书在挑战发放后改变，须保留旧记录并重新冻结需求')
    except (OSError,ValueError,TypeError) as error:
        issues.append('挑战记录：'+str(error))
    kinds=set()
    paths=set()
    artifacts=record.get('artifacts',[])
    if not isinstance(artifacts,list):artifacts=[];issues.append('artifacts须为数组')
    for artifact in artifacts:
        try:
            if not isinstance(artifact,dict):raise ValueError('产物条目须为对象')
            kind=artifact.get('kind')
            if kind not in {'normal','variant','failure_recovery'}:raise ValueError('未知产物类型')
            path=scoped_path(artifact.get('path'),['course/learner_artifacts','reports/learner'])
            if path in paths:raise ValueError('三类产物须分别运行记录，不能复用同一文件')
            paths.add(path)
            if not HEX64.fullmatch(str(artifact.get('sha256',''))) or digest(path)!=artifact['sha256']:
                raise ValueError('产物哈希不匹配')
            payload=read_object(path)
            if payload.get('kind')!=kind:raise ValueError('产物类型与记录不匹配')
            if payload.get('producer')!='learner' or payload.get('day')!=day or payload.get('implementation_commit')!=commit:
                raise ValueError('产物不是本课、本次实现的本人报告')
            if not challenge or payload.get('challenge_id')!=challenge.get('id'):
                raise ValueError('产物未绑定本轮挑战')
            for key in ('environment','input','expected','actual','run_at'):
                if key not in payload or payload[key] is None:raise ValueError('产物缺少'+key)
            if payload.get('passed') is not True:raise ValueError('产物没有报告成功，保留失败但不可用于通过')
            if kind=='failure_recovery' and (not payload.get('failure_observed') or not payload.get('recovery_observed')):
                raise ValueError('缺少实际失败与恢复观察')
            kinds.add(kind)
        except (OSError,ValueError,TypeError) as error:
            issues.append('产物：'+str(error))
    if kinds!={'normal','variant','failure_recovery'}:
        issues.append('须分别提供正常、需求变体、失败恢复三类本人产物')
    if day==25:
        validate_jobs(record.get('jobs'),issues)
    review=record.get('review',{})
    if not isinstance(review,dict):review={};issues.append('review须为对象')
    if review.get('critical_violations'):
        issues.append('存在关键违规，不允许用总分抵消')
    result['status']='invalid_evidence' if issues else 'pending_review'
    if issues:return result
    critical={f'D{day}-C{i}' for i in range(1,len(catalog(day)['checks'])+1)}
    checks=review.get('critical_checks',{})
    if review.get('status')=='accepted':
        if not (review.get('reviewer') and review.get('reviewed_at') and review.get('notes')):
            issues.append('通过复核必须记录复核者、日期和具体依据')
        if review.get('novel_requirement_confirmed') is not True:
            issues.append('公开抽签不能自动认证未见需求，须复核者确认')
        if not isinstance(checks,dict) or set(checks)!=critical or any(checks[k] is not True for k in critical):
            issues.append('本课所有关键项必须逐项通过')
        if issues:result['status']='review_incomplete'
        else:result.update(status='accepted_by_recorded_review',completion_eligible=True)
    elif review.get('status')=='rejected':
        result['status']='review_rejected'
    return result


def validate_jobs(jobs,issues):
    if not isinstance(jobs,list) or not 5<=len(jobs)<=10:
        issues.append('Day25须5–10个真实目标岗位');return
    urls=set();primary=False
    for job in jobs:
        if not isinstance(job,dict):issues.append('岗位条目须为对象');continue
        url=job.get('source_url','')
        if not isinstance(url,str) or not url.startswith('https://') or url in urls:
            issues.append('岗位须有不同的HTTPS来源链接')
        urls.add(str(url))
        if not job.get('captured_at') or not job.get('role_family'):issues.append('岗位缺少采集日期或岗位族')
        primary=primary or job.get('primary') is True
        requirements=job.get('requirements')
        if not isinstance(requirements,list) or not requirements:issues.append('岗位要求映射为空');continue
        for requirement in requirements:
            if not isinstance(requirement,dict):issues.append('要求条目须为对象');continue
            if not requirement.get('requirement') or requirement.get('priority') not in {'must','nice'}:
                issues.append('岗位要求须区分must/nice')
            if job.get('primary') is True and requirement.get('priority')=='must':
                if requirement.get('gap_status')!='closed' or not requirement.get('evidence'):
                    issues.append('主目标核心要求缺口未闭合，不可记Day25完成')
            elif not requirement.get('evidence') and not requirement.get('gap_plan'):
                issues.append('加分项/其他目标缺口须有证据或具体补缺计划')
    if not primary:issues.append('至少指定一个主目标岗位')


def assess_day(day):
    item=lesson(day)
    try:
        record=read_object(PROJECT_ROOT/item['submission'])
        value=evaluate_record(day,record)
    except (OSError,ValueError,TypeError) as error:
        value={'day':day,'status':'invalid_evidence','completion_eligible':False,'issues':[str(error)],'hard_gate':item['hard_gate']}
    previous=[gate for gate in GATES if gate<day]
    if day==19:
        profile=read_profile()
        historical=set(profile.get('completed_stages',[])) if profile.get('track')=='alexstudy' else set()
        previous+=[stage for stage in range(1,19) if stage not in historical]
    if day==24:previous+=list(range(20,24))
    if day==26:previous.append(25)
    blocked=[other for other in sorted(set(previous)) if not assess_day(other)['completion_eligible']]
    value['blocked_by_days']=blocked
    if blocked:
        value['completion_eligible']=False
        if value['status']=='accepted_by_recorded_review':value['status']='blocked_by_prerequisite_gate'
    value['submission_file']=item['submission']
    value['critical_criteria']={f'D{day}-C{i}':s for i,s in enumerate(catalog(day)['checks'],1)}
    return value
