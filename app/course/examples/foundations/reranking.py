"""Day 6 新作业：调用成对评分器，对已有候选重新排序。"""
from app.paths import PROJECT_ROOT

from collections.abc import Callable, Sequence


def rerank_candidates(
        question: str,
        candidates: list[dict],
        score_pairs: Callable[[list[tuple[str, str]]], Sequence[float]],
        top_k: int = 2,
) -> list[dict]:
    """本轮只实现这个函数；真实模型加载由助教后续适配。

    candidates 为已去重、有序的 [{"chunk": 六字段片段, "score": 检索分数}, ...]。
    score_pairs 是可调用对象，接收 [(问题, 候选正文), ...]；返回同顺序的一维分数。
    一次传入全部候选，只调用评分器一次；不能先截为 top_k 再评分。

    返回新的命中列表，每项包含：
    chunk：原片段（ID 和正文不改）；
    score：float(新评分)，用于本轮排序；
    retrieval_score：float(原来的检索分数)，便于追踪。
    按新 score 稳定降序排序，返回前 top_k 条，不修改 candidates。
    top_k < 1 先抛 ValueError；候选为空直接返回 []，不调用评分器。
    评分数与候选数不同抛 ValueError，不能让 zip 静默遗漏候选。

    score_pairs 类型的含义：接收“字符串二元组的列表”，返回“浮点数序列”。
    本函数中将它当普通函数调用即可，不需要实现神经网络或导入模型库。
    """
    if top_k < 1:
        raise ValueError
    results = []
    if len(candidates) < 1:
        return results
    pairs = []
    for candidate in candidates:
        pairs.append((question, candidate["chunk"]["content"]))
        results.append({
            "chunk": candidate["chunk"],
            "score": 0.0,
            "retrieval_score": float(candidate["score"])
        })
    scores = score_pairs(pairs)
    if len(candidates) != len(scores):
        raise ValueError
    for index, score in enumerate(scores):
        results[index]["score"] = float(score)
    results = sorted(
        results,
        key=lambda item: item["score"],
        reverse=True
    )
    return results[:top_k]
