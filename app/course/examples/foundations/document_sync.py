"""Day 7 作业一：对同一知识源的完整快照生成逐文档同步计划。"""
from app.paths import PROJECT_ROOT


def plan_document_sync(
    current_documents: list[dict],
    incoming_documents: list[dict],
    *,
    complete_snapshot: bool = False,
) -> list[dict[str, str]]:
    """只实现本函数，不执行 SQL、不编码向量。

    两个列表已由调用方限定为同一知识源。每项是助教生成的文档清单：
    {"id": 稳定文档ID, "version": 版本标记,
     "vector_fingerprint": 向量输入及模型配置的指纹,
     "metadata_fingerprint": 来源版本及访问元数据的指纹}。

    complete_snapshot=False 时先抛 ValueError：分页结果或一次上传列表不能据此删库。
    两个列表各自的 id 必须唯一；任一列表有重复 id 则抛 ValueError。

    先按 incoming_documents 顺序，为每份文档生成一项：
    - 当前不存在该 id：REINDEX。
    - 存在，但 vector_fingerprint 不同：REINDEX（优先于元数据比较）。
    - 向量指纹相同，但 metadata_fingerprint 不同：METADATA_ONLY。
    - 两种指纹都相同：UNCHANGED。
    再按 current_documents 顺序，给新完整快照不再包含的 id 追加 DELETE。

    每项返回恰好两个键：{"document_id": id, "action": 上述四种动作之一}。
    两个输入均为空时返回 []；新的完整快照为空时，为所有当前文档计划 DELETE。
    这是计划阶段，不实际删除；读取失败不能被调用方转换为空快照。
    不修改输入，不硬编码教学文档 ID，不根据版本字符串的字面大小判断新旧。

    提示：用 id → 文档清单的字典查找旧记录；用 set 判断新快照的 ID 成员。
    """
    if not complete_snapshot:
        raise ValueError("必须提供同一知识源的完整快照")
    if any(
        len({doc["id"] for doc in docs}) != len(docs)
        for docs in (current_documents,incoming_documents)
    ):
        raise ValueError("存在重复文档ID")
    current_by_id = {doc["id"]: doc for doc in current_documents}
    results = []
    for incoming_document in incoming_documents:
        if (incoming_document["id"] not in current_by_id or
                current_by_id[incoming_document["id"]]["vector_fingerprint"]
                != incoming_document["vector_fingerprint"]):
            results.append({
                    "document_id": incoming_document["id"],
                    "action": "REINDEX"
                })
        elif current_by_id[incoming_document["id"]]["metadata_fingerprint"] != incoming_document["metadata_fingerprint"]:
            results.append({
                    "document_id": incoming_document["id"],
                    "action": "METADATA_ONLY"
                })
        else:
            results.append({
                    "document_id": incoming_document["id"],
                    "action": "UNCHANGED"
                })
    incoming_by_id = {doc["id"]: doc for doc in incoming_documents}
    for current_document in current_documents:
        if current_document["id"] not in incoming_by_id:
            results.append({
                "document_id": current_document["id"],
                "action": "DELETE"
            })
    return results
