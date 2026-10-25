"""长期偏好仅允许表达风格；不存用户身份、额度或确认凭据。"""
from app.pgvector_store import connect_database


def preference(run_id: str, user_id: str, tone: str | None=None, delete: bool=False):
    with connect_database() as c:
        if delete:
            c.execute('DELETE FROM leave_workflow_lab.web_preferences WHERE run_id=%s AND user_id=%s',(run_id,user_id))
        elif tone is not None:
            if tone not in ('concise','detailed'):
                raise ValueError('只允许concise/detailed')
            c.execute('INSERT INTO leave_workflow_lab.web_preferences(run_id,user_id,tone) VALUES(%s,%s,%s) ON CONFLICT(run_id,user_id) DO UPDATE SET tone=excluded.tone,updated_at=now()',(run_id,user_id,tone))
        row=c.execute('SELECT tone,updated_at FROM leave_workflow_lab.web_preferences WHERE run_id=%s AND user_id=%s',(run_id,user_id)).fetchone()
    return {'tone':row['tone'] if row else None,'stored':row is not None}
