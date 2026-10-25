"""Validate the 26-unit repository and its branch-specific initialized state."""
from pathlib import Path
import ast
import json
import tomllib
import hashlib
from app.paths import PROJECT_ROOT
from app.course.profile import read_profile


def main():
    root=PROJECT_ROOT
    assert [p.name for p in root.glob('*.md')]==['README.md'],'Only README.md belongs at repository root'
    for name in ('LICENSE','pyproject.toml','docs/deployment.md','docs/architecture.md','docs/contributing.md','docs/security.md'):
        assert (root/name).is_file(),name
    assert tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['name']=='llm-engineer-lab'
    manifest=json.loads((root/'course/manifest.json').read_text(encoding='utf-8'))
    assert [row['day'] for row in manifest['lessons']]==list(range(1,27))
    for row in manifest['lessons']:
        for field in ('lesson','assignment','project','task','solution','reference','submission'):
            assert (root/row[field]).is_file(),row[field]
    modules=json.loads((root/'course/foundation_exercises.json').read_text(encoding='utf-8'))['modules']
    profile=read_profile()
    if profile['track']=='starter':
        assert profile['initialized'] is True and profile['completed_stages']==[] and profile['next_day']==1
        for name,functions in modules.items():
            tree=ast.parse((root/f'app/{name}.py').read_text(encoding='utf-8-sig'))
            for target in functions:
                function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==target)
                statements=function.body
                if statements and isinstance(statements[0],ast.Expr) and isinstance(statements[0].value,ast.Constant) and isinstance(statements[0].value.value,str):statements=statements[1:]
                assert len(statements)==1 and isinstance(statements[0],ast.Raise),name+'.'+target
                assert isinstance(statements[0].exc,ast.Call) and getattr(statements[0].exc.func,'id',None)=='NotImplementedError'
        frozen=json.loads((root/'data/retrieval_lab_v2/freeze.json').read_text(encoding='utf-8'))
        for filename,expected in frozen['files_sha256'].items():
            assert hashlib.sha256((root/'data/retrieval_lab_v2'/filename).read_bytes()).hexdigest()==expected,filename
        for row in manifest['lessons']:
            record=json.loads((root/row['submission']).read_text(encoding='utf-8'))
            assert record['status']=='not_started' and record['review']['status']=='pending'
    else:
        assert profile['track']=='alexstudy' and profile['completed_stages']==list(range(1,12))
    print(json.dumps({'project':'llm-engineer-lab','lessons':26,'track':profile['track'],'status':'passed','scope':'structure_and_declared_starter_state_not_learner_mastery'},ensure_ascii=False))


if __name__=='__main__':main()
