"""Day18 作业。先读course/lessons/day18.md，参考答案另存course/solutions。"""

def classify_failure(stage: str, committed: bool, error_type: str) -> dict:
    """返回category/action/safe_to_claim_not_submitted。已提交优先post_commit/read_status_then_retry_same_key/False；APIConnectionError或APITimeoutError为model_transport/bounded_retry/True；business阶段为business_rule/show_reason_no_blind_retry/True；其余system/inspect_trace/True。"""
    raise NotImplementedError("请按课件契约实现")
