"""只读报告：查询本人部门的聚合，不返回同事个人申请明细。"""
from app.pgvector_store import connect_database


def department_report(run_id: str, user_id: str) -> dict:
    with connect_database() as c, c.transaction():
        c.execute('SET TRANSACTION READ ONLY')
        person=c.execute('SELECT display_name,department FROM leave_workflow_lab.web_users WHERE run_id=%s AND user_id=%s',(run_id,user_id)).fetchone()
        if not person:
            raise PermissionError('未知账号')
        stats=c.execute("SELECT count(*) AS application_count,coalesce(sum(a.requested_days),0)::integer AS total_days FROM leave_workflow_lab.applications a JOIN leave_workflow_lab.web_users u ON u.run_id=a.run_id AND u.user_id=a.user_id WHERE a.run_id=%s AND u.department=%s AND a.status='PENDING_APPROVAL'",(run_id,person['department'])).fetchone()
    return {'department':person['department'],**stats,'status_scope':'PENDING_APPROVAL','unit':'天','source':'actual_teaching_applications','not_approved_leave':True}
