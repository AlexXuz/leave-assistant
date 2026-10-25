"""Day20 作业。先读course/lessons/day20.md，参考答案另存course/solutions。"""

def choose_intervention(failure: str) -> str:
    """映射：missing_document→fix_ingestion；missing_candidate→fix_retrieval；bad_ranking→rerank；wrong_live_balance→fix_business_tool；stale_confirmation→fix_workflow；format_style_consistent→consider_sft；ambiguous_requirement→clarify；其他collect_evidence。同时阅读参考答案的validate_splits并在作业中补实现它。"""
    raise NotImplementedError("请按课件契约实现")

def validate_splits(rows: list[dict]) -> dict:
    """按scenario_id检查train/validation/test不交叉，并返回三份行数。"""
    raise NotImplementedError("检查场景级数据泄漏")
