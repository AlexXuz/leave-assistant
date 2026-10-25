"""RAG 第一项：按当前制度的 Markdown 二级标题切分，并保留来源元数据。"""

from app.policy_qa import load_policy_documents


def split_policy_document(document: dict[str, str]) -> list[dict[str, str]]:
    """本轮作业：实现这个函数，不调用模型。

    输入已包含 id/title/version/content，由下面的读取函数提供。
    仅处理当前教学格式：# 总标题、头部元数据、## 二级章节、章节正文。

    按每个以 '## ' 开头的标题分组，正文直到下一个二级标题或文件结束。
    忽略第一个二级标题前的总标题和文件元数据；跳过没有正文的空章节。
    不按单句拆，不在章节内重复切分；正文两端 strip，内部换行保留。

    返回按原顺序排列的列表，每项恰含六个字符串字段：
    id: f"{document['id']}:{document['version']}:{序号}"，序号从 1 开始。
    document_id/title/version: 继承输入的 id/title/version。
    heading: 二级标题文本，不含 '## '。
    content: f"{总标题}\n{章节标题}\n{章节正文}"。

    例：leave-policy:2026-10-15-v1:2 对应“年假审批”。
    不修改输入。不要把 7 个已知章节硬编码进函数。
    提示：循环内遇到新标题时保存上一节，循环结束后还要保存最后一节。
    """
    raise NotImplementedError("请完成 split_policy_document；输入输出与验收见网页课程")


def rank_chunks(query_vector, chunk_vectors, chunks: list[dict], top_k: int = 2) -> list[dict]:
    """下一项作业：对已经归一化的向量计算相似度，返回 Top-K。

    query_vector: 形状 (维度数,) 的 NumPy 数组。
    chunk_vectors: 形状 (片段数, 维度数) 的 NumPy 数组。
    chunks[i] 对应 chunk_vectors[i]，顺序不得混淆。

    返回 [{"chunk": 原片段字典, "score": Python float}, ...]。
    按 score 降序；同分保留原片段顺序。最多 top_k 项，top_k 大于数量时返回全部。
    top_k 小于 1 时抛 ValueError；空片段列表返回 []。
    不修改输入，不调用任何模型，不设置人为的“正确答案阈值”。

    可用 @ 计算归一化向量点积；也可以逐行计算。
    浮点分数用 float(...) 转成可 JSON 序列化的 Python 数值。
    """
    raise NotImplementedError("请完成 rank_chunks；输入输出与验收见网页课程")


# 以下是已提供的元数据读取，不是本轮作业。
def load_documents_for_chunking() -> list[dict[str, str]]:
    results = []
    for document in load_policy_documents():
        lines = document["content"].splitlines()
        title = next((line[2:].strip() for line in lines if line.startswith("# ")), "")
        version = next((line.removeprefix("版本：").strip() for line in lines if line.startswith("版本：")), "")
        if not title or not version:
            raise ValueError(f"文档缺少总标题或版本：{document['id']}")
        results.append({**document, "title": title, "version": version})
    return results
