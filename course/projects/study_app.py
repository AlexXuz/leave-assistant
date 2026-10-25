"""HTTP shell for independent projects, with a separate persistent teaching run.

Launch: python -m uvicorn course.projects.study_app:app --host 127.0.0.1 --port 8014
The existing demo UI/auth/business services are reused; independent routes are
learner-owned. This is not a completed integration assignment.
"""
from dataclasses import dataclass
from fastapi import HTTPException, Request
from app.leave_web import COOKIE, create_app
from app.leave_web_accounts import current_user
from app.pgvector_store import connect_database

RUN_ID='day12-web-independent-v2'


@dataclass(frozen=True)
class StudyIdentity:
    run_id: str
    user_id: str
    username: str
    department: str


def require_identity(request: Request) -> StudyIdentity:
    """Call this from new endpoints. Never accept an identity from body/model text."""
    token=request.cookies.get(COOKIE,'')
    if not token:
        raise HTTPException(401,'请先在这个独立练习页面登录。')
    with connect_database() as connection:
        value=current_user(connection,RUN_ID,token)
    if not value:
        raise HTTPException(401,'会话无效，请在独立练习页面重新登录。')
    return StudyIdentity(RUN_ID,value['user_id'],value['username'],value['department'])


app=create_app(RUN_ID)
# Import after the shell helpers exist; learner routers can use require_identity.
from course.projects.study_routes import router
app.include_router(router)
