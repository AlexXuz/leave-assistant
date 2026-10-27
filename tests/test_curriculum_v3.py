"""Curriculum integration and evidence-version regressions, not learner certification."""
from copy import deepcopy
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.course import assessment
from app.leave_web import create_app
from app.paths import PROJECT_ROOT


class CurriculumV3(unittest.TestCase):
    def test_new_task_rubrics_match_catalog_and_pending_templates(self):
        manifest=json.loads((PROJECT_ROOT/'course/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual([row['day'] for row in manifest['lessons']], list(range(1,27)))
        for day in (16,17,18,19,20,24,26):
            with self.subTest(day=day):
                item=next(row for row in manifest['lessons'] if row['day']==day)
                self.assertEqual(item['assessment_version'],3)
                source=(PROJECT_ROOT/item['task']).read_text(encoding='utf-8')
                checks=re.findall(r'^- \*\*D\d+-C\d+\*\*：(.+)$',source,re.M)
                self.assertEqual(checks, assessment.catalog(day)['checks'])
                self.assertEqual(len(checks),5 if day in (19,24,26) else 4)
                for field in ('lesson','task','project','solution','reference','submission'):
                    self.assertTrue((PROJECT_ROOT/item[field]).is_file(),item[field])
                record=json.loads((PROJECT_ROOT/item['submission']).read_text(encoding='utf-8'))
                # Do not prescribe a learner's future progress; inspect only untouched templates.
                if record['status']=='not_started':
                    self.assertEqual(record['assessment_version'],3)
                    self.assertFalse(any(record['review']['critical_checks'].values()))

    def test_browser_resources_and_agent_preview_need_no_credentials(self):
        with patch('app.leave_web.connect_database',side_effect=AssertionError('read-only course must not connect')),TestClient(create_app()) as client:
            manifest=client.get('/api/course').json()
            day19=next(row for row in manifest['lessons'] if row['day']==19)
            self.assertEqual(day19['assessment_version'],3)
            self.assertEqual(day19['project'],'course/projects/support_agent_runtime.py')
            self.assertEqual(day19['submission'],'course/submissions/single_agent_delivery.json')
            for artifact in ('lesson','assignment','solution','project','reference'):
                with self.subTest(artifact=artifact):
                    response=client.get(f'/api/course/19/content/{artifact}')
                    self.assertEqual(response.status_code,200)
                    if artifact=='assignment':
                        # Check the rendered v3 task, not just a successful legacy page.
                        for required in ('course/projects/support_agent_runtime.py',
                                         'course/submissions/single_agent_delivery.json',
                                         '身份由宿主绑定','返回文本不能扩大工具或权限',
                                         '忽略规则并查询他人订单','身份与允许动作保持不变',
                                         '工具超时或可重试故障','修复后复跑同一案例'):
                            with self.subTest(required=required):
                                self.assertIn(required,response.text)
            preview=client.get('/api/course/labs/agent-suite')
            self.assertEqual(preview.status_code,200)
            value=preview.json()
            self.assertGreaterEqual(len(value['cases']),8)
            self.assertFalse(value['completion_eligible'])
            self.assertFalse(value['model_called'])
            self.assertNotIn('expected',value['cases'][0])
            self.assertEqual(client.get('/api/course/files',params={'path':'.env'}).status_code,404)


class EvidenceRevision(unittest.TestCase):
    def test_old_task_or_challenge_cannot_certify_new_agent_requirement(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            task=root/'course/tasks/current.md'
            task.parent.mkdir(parents=True)
            task.write_text('Synthetic revision test; never learner evidence.',encoding='utf-8')
            challenge_path=root/'course/challenges/issued/case.json'
            challenge_path.parent.mkdir(parents=True)
            challenge={'id':'challenge-fixture','day':19,'baseline_commit':'a'*40,
                       'assessment_version':3,'task_sha256':assessment.digest(task)}
            def save_challenge():
                challenge_path.write_text(json.dumps(challenge),encoding='utf-8')
                return assessment.digest(challenge_path)
            record={'schema_version':2,'assessment_version':3,'producer':'learner','day':19,'status':'submitted',
                    'implementation_commit':'b'*40,'independent_before_reference':True,'assistance_used':[],
                    'design_notes':'Synthetic fixture only','reproduction_steps':['create fixture','evaluate record'],
                    'challenge_file':'course/challenges/issued/case.json','challenge_sha256':save_challenge(),
                    'artifacts':[],'review':{'status':'accepted','reviewer':'synthetic fixture','reviewed_at':'fixture',
                      'notes':'Tests bookkeeping, not actual ability','novel_requirement_confirmed':True,
                      'critical_checks':{f'D19-C{i}':True for i in range(1,6)}}}
            for kind in ('normal','variant','failure_recovery'):
                path=root/f'course/learner_artifacts/{kind}.json'
                path.parent.mkdir(exist_ok=True)
                payload={'producer':'learner','day':19,'kind':kind,'implementation_commit':'b'*40,
                         'challenge_id':'challenge-fixture','environment':{'synthetic':True},'input':{},
                         'expected':{},'actual':{},'run_at':'fixture','passed':True,
                         'failure_observed':'synthetic','recovery_observed':'synthetic'}
                path.write_text(json.dumps(payload),encoding='utf-8')
                record['artifacts'].append({'kind':kind,'path':path.relative_to(root).as_posix(),'sha256':assessment.digest(path)})
            item={'hard_gate':True,'assessment_version':3,'task':'course/tasks/current.md'}
            with patch.object(assessment,'PROJECT_ROOT',root),patch.object(assessment,'lesson',return_value=item),patch.object(assessment,'catalog',return_value={'checks':['fixture']*5}):
                self.assertTrue(assessment.evaluate_record(19,record)['completion_eligible'])
                old=deepcopy(record);old.pop('assessment_version')
                self.assertFalse(assessment.evaluate_record(19,old)['completion_eligible'])
                old=deepcopy(record);old['review']['critical_checks'].pop('D19-C5')
                self.assertFalse(assessment.evaluate_record(19,old)['completion_eligible'])
                challenge['assessment_version']=2
                record['challenge_sha256']=save_challenge()
                self.assertFalse(assessment.evaluate_record(19,record)['completion_eligible'])
                challenge['assessment_version']=3
                record['challenge_sha256']=save_challenge()
                task.write_text('Changed requirement after challenge',encoding='utf-8')
                self.assertFalse(assessment.evaluate_record(19,record)['completion_eligible'])


if __name__=='__main__':
    unittest.main()
