"""参考答案：条件边只返回节点名，不执行确认/提交。"""
def route_leave_workflow(state: dict) -> str:
    if state['draft_status'] == 'SUBMITTED':
        if not state['application_id']:
            raise ValueError('已提交却无申请编号')
        return 'show_result'
    if state['application_id']:
        raise ValueError('未提交状态却有申请编号')
    if state['missing_fields']:
        return 'request_details'
    routes = {'BLOCKED':'explain_block','READY_FOR_CONFIRMATION':'wait_confirmation','CONFIRMED':'submit'}
    if state['draft_status'] not in routes:
        raise ValueError('需要重新预检')
    return routes[state['draft_status']]
