"""按需发现/加载课程Skill，只允许执行已知脚本；不是任意代码沙箱。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import yaml
from app.pgvector_store import PROJECT_ROOT

ROOT=PROJECT_ROOT/'course/skills'


def discover() -> list[dict]:
    result=[]
    for folder in sorted(ROOT.iterdir()):
        source=folder/'SKILL.md'
        if source.is_file():
            text=source.read_text(encoding='utf-8')
            meta=yaml.safe_load(text.split('---',2)[1])
            if meta['name']!=folder.name:
                raise ValueError('Skill目录与名称不一致')
            result.append({'name':meta['name'],'description':meta['description']})
    return result


def execute_report(run_id: str, user_id: str) -> dict:
    selected=next(x for x in discover() if x['name']=='leave-report')
    folder=ROOT/selected['name']
    instructions=(folder/'SKILL.md').read_text(encoding='utf-8')
    reference=(folder/'references/scope.md').read_text(encoding='utf-8')
    env={k:os.environ[k] for k in ('PATH','SYSTEMROOT','TEMP','TMP','PGHOST','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSSLMODE') if k in os.environ}
    env.update(COURSE_REPORT_RUN=run_id,COURSE_REPORT_USER=user_id,PYTHONPATH=str(PROJECT_ROOT),PYTHONIOENCODING='utf-8')
    process=subprocess.run([sys.executable,'-X','utf8',str(folder/'scripts/render_report.py')],cwd=PROJECT_ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
    if process.returncode:
        raise RuntimeError('报告脚本失败，请检查本机数据库')
    return {'discovered':discover(),'loaded':['SKILL.md','references/scope.md','assets/report.md'],
            'script':'scripts/render_report.py','instruction_characters':len(instructions)+len(reference),
            **json.loads(process.stdout),'execution_policy':'fixed_reviewed_script_only','model_called':False}
