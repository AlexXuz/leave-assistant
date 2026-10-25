"""Day 6 核心作业：用排名融合多个检索结果；不访问数据库或模型。"""
from app.paths import PROJECT_ROOT


def fuse_rrf(
    rankings: list[list[dict]], top_k: int = 2, rank_constant: int = 60
) -> list[dict]:
    """本轮仅实现这个函数：等权 Reciprocal Rank Fusion。

    rankings 是多路有序命中列表，例如 [vector_hits, bm25_hits]。
    每个命中仍为 {"chunk": 六字段片段字典, "score": 原检索分数}。
    对每一路，从 1 开始数排名；出现的片段获得 1 / (rank_constant + 排名)。
    相同 chunk['id'] 跨路累加贡献；没有出现在某一路中，该路贡献为 0。
    不使用原始 score 算融合分数；两种分数不在同一尺度。

    返回最多 top_k 项 [{"chunk": 原片段, "score": Python float 融合分数}, ...]。
    按融合分数降序，同分保持首次遇到片段的顺序（先前一路，再后一路）。
    同一路重复 ID 只计第一次出现的贡献；名次取原列表位置，不重新编号。
    跨路相同 ID 的 chunk 内容按契约一致，保留首次遇到的 chunk。
    top_k < 1 或 rank_constant < 1：抛 ValueError。所有路为空时返回 []。
    不修改 rankings 或内部 hit；不要给原始 hit 的 score 直接赋新值。

    实现思路：一个按 ID 累积分数的字典；每一路各有自己的 seen 集合。
    构建新的命中字典，再稳定降序排序并切片。
    """
    if top_k < 1 or rank_constant < 1:
        raise ValueError
    merged = {}
    for hits in rankings:
        seen = set()
        for rank, hit in enumerate(hits, start=1):
            identifier = hit["chunk"]["id"]
            if identifier in seen:
                continue
            contribution = 1.0/(rank + rank_constant)
            if identifier not in merged:
                merged[identifier] = {
                    "chunk": hit["chunk"],
                    "score": 0.0
                }
            merged[identifier]["score"] += contribution
            seen.add(identifier)
    results = sorted(
        merged.values(),
        key=lambda item: item["score"],
        reverse=True
    )
    return results[:top_k]
