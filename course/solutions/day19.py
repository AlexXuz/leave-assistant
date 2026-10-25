"""参考：合并工具结果时保留不同数据来源，不把制度证据当余额。"""
def merge_evidence(balance: dict, policy: dict) -> dict:
    if balance.get('status') not in {'ok','not_found','error'}:
        raise ValueError('未知业务状态')
    evidence=policy.get('evidence',[])
    sources=[item['id'] for item in evidence]
    if len(sources)!=len(set(sources)):
        sources=list(dict.fromkeys(sources))
    return {'balance_status':balance['status'],'remaining_days':balance.get('remaining_days') if balance['status']=='ok' else None,
            'policy_evidence':evidence,'allowed_policy_sources':sources,'can_submit':False}
