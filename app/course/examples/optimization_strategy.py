"""参考：先按失败阶段选优化，不因为有微调工具就开始训练。"""
def choose_intervention(failure: str) -> str:
    return {'missing_document':'fix_ingestion','missing_candidate':'fix_retrieval','bad_ranking':'rerank',
            'wrong_live_balance':'fix_business_tool','stale_confirmation':'fix_workflow',
            'format_style_consistent':'consider_sft','ambiguous_requirement':'clarify'}.get(failure,'collect_evidence')


def validate_splits(rows: list[dict]) -> dict:
    groups = {}
    for row in rows:
        if row['split'] not in {'train','validation','test'}:
            raise ValueError('未知数据划分')
        group = row['scenario_id']
        if group in groups and groups[group] != row['split']:
            raise ValueError('同一场景的改写跨数据集，发生泄漏')
        groups[group] = row['split']
    return {name:sum(r['split']==name for r in rows) for name in ('train','validation','test')}
