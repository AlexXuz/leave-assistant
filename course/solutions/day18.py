"""参考：失败阶段分类；禁止把业务已提交后的展示失败当作提交失败。"""
def classify_failure(stage: str, committed: bool, error_type: str) -> dict:
    if committed:
        return {'category':'post_commit','action':'read_status_then_retry_same_key','safe_to_claim_not_submitted':False}
    if error_type in {'APIConnectionError','APITimeoutError'}:
        return {'category':'model_transport','action':'bounded_retry','safe_to_claim_not_submitted':True}
    if stage == 'business':
        return {'category':'business_rule','action':'show_reason_no_blind_retry','safe_to_claim_not_submitted':True}
    return {'category':'system','action':'inspect_trace','safe_to_claim_not_submitted':True}
