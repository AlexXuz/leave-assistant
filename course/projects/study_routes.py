"""Learner-owned HTTP adapter. Add independent project routes here.

Only the identity inspection endpoint is provided. Call require_identity(request)
inside each route, construct service adapters and invoke your project module.
Do not return a made-up success or call author examples instead of your code.
"""
from fastapi import APIRouter, Request

router=APIRouter(prefix='/api/independent')


@router.get('/context')
def context(request: Request):
    from course.projects.study_app import require_identity
    identity=require_identity(request)
    return {'run_id':identity.run_id,'username':identity.username,'department':identity.department,
            'scope':'authenticated_shell_only','independent_workflow_implemented':False}
