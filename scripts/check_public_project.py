"""Validate the 26-unit repository and its branch-specific initialized state."""
from pathlib import Path
import ast
import json
import tomllib
import hashlib
from app.paths import PROJECT_ROOT
from app.course.profile import read_profile


FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def assert_unimplemented(function, label):
    statements = function.body
    if (statements and isinstance(statements[0], ast.Expr)
            and isinstance(statements[0].value, ast.Constant)
            and isinstance(statements[0].value.value, str)):
        statements = statements[1:]
    assert len(statements) == 1 and isinstance(statements[0], ast.Raise), label
    error = statements[0].exc
    assert isinstance(error, ast.Call) and getattr(error.func, 'id', None) == 'NotImplementedError', label


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
                function=next(node for node in tree.body if isinstance(node,FUNCTION_NODES) and node.name==target)
                assert_unimplemented(function,name+'.'+target)
        for filename, names in {
            'scripts/evaluate_leave.py': ('compare_result', 'classify_error'),
            'app/leave_graph_routing.py': ('route_leave_workflow',),
        }.items():
            tree=ast.parse((root/filename).read_text(encoding='utf-8-sig'))
            for name in names:
                function=next(node for node in tree.body if isinstance(node,FUNCTION_NODES) and node.name==name)
                assert_unimplemented(function,filename+':'+name)
        # Only two HTTP/auth helpers are supplied infrastructure. Top-level
        # project/assignment functions, including async entries, are learner work.
        supplied_helpers={('course/projects/study_app.py','require_identity'),
                          ('course/projects/study_routes.py','context')}
        for folder in ('course/projects', 'course/assignments'):
            for path in sorted((root/folder).glob('*.py')):
                tree=ast.parse(path.read_text(encoding='utf-8-sig'))
                for function in tree.body:
                    if not isinstance(function,FUNCTION_NODES):
                        continue
                    relative=path.relative_to(root).as_posix()
                    if (relative,function.name) not in supplied_helpers:
                        assert_unimplemented(function,relative+':'+function.name)
        frozen=json.loads((root/'data/retrieval_lab_v2/freeze.json').read_text(encoding='utf-8'))
        for filename,expected in frozen['files_sha256'].items():
            assert hashlib.sha256((root/'data/retrieval_lab_v2'/filename).read_bytes()).hexdigest()==expected,filename
        candidate=json.loads((root/'data/retrieval_lab_v2/rerank_candidate_v1.json').read_text(encoding='utf-8'))
        assert candidate['freeze']==frozen
        assert hashlib.sha256((root/candidate['development_report']).read_bytes()).hexdigest()==candidate['development_report_sha256']
        for path in sorted((root/'course/submissions').glob('*.json')):
            record=json.loads(path.read_text(encoding='utf-8'))
            assert record['status']=='not_started' and record['review']['status']=='pending'
            assert not record['artifacts'] and not any(record['review']['critical_checks'].values()),path.name
            for field in ('implementation_commit','challenge_file','challenge_sha256'):
                assert record.get(field) is None,path.name+':'+field
    else:
        assert profile['track']=='alexstudy' and profile['completed_stages']==list(range(1,12))
    print(json.dumps({'project':'llm-engineer-lab','lessons':26,'track':profile['track'],'status':'passed','scope':'structure_and_declared_starter_state_not_learner_mastery'},ensure_ascii=False))


if __name__=='__main__':main()
