"""检索评测作业：只实现 evaluate_evidence，不加载模型。"""
from app.paths import PROJECT_ROOT


def evaluate_evidence(retrieved_ids: list[str], required_ids: list[str]) -> dict:
    """比较命中片段 ID 与人工标注的必要证据 ID。

    返回恰好三个字段：
    evidence_recall: 找回的不同必要 ID 数 / 不同必要 ID 总数，Python float。
    all_required_found: 是否找齐全部必要证据，Python bool。
    missing_ids: 未找回的必要 ID，去重并按字符串升序排列。

    retrieved_ids 可能包含无关 ID 或重复 ID；重复不能增加召回率。
    required_ids 中的重复 ID 也只算一份证据。
    retrieved_ids 为空、required_ids 非空：召回率 0.0，未找齐。s
    required_ids 为空：抛 ValueError。本函数只评有必要证据的题目，
    不把未知婚假/个人余额等无答案问题算作召回成功。
    不修改输入，不调用模型，不读取文件。

    示例：evaluate_evidence(["remote", "other"], ["leave", "remote"])
    -> {"evidence_recall": 0.5, "all_required_found": False,
        "missing_ids": ["leave"]}

    提示：set(列表) 可去重，& 可求两个集合的交集，- 可求差集；
    len 求数量，sorted(集合) 得到排序后的列表。也可以用循环实现。
    """
    required = set(required_ids)
    if not required:
        raise ValueError("必要证据不能为空")
    found = required & set(retrieved_ids)
    missing = set(required_ids) - set(retrieved_ids)
    evidence_recall = len(found)/len(required)
    all_required_found = True
    if evidence_recall < 1:
        all_required_found = False
    result = {
        "evidence_recall": evidence_recall,
        "all_required_found": all_required_found,
        "missing_ids": sorted(missing)
    }
    return result
