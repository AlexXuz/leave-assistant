"""Day 7 作业二：将同步计划和准备好的向量作为一批原子操作执行。"""
from app.paths import PROJECT_ROOT

from app.document_sync_store import advance_source, delete_document, lock_source, replace_document


def apply_sync_batch(connection, batch: dict) -> dict:
    """本轮只实现此函数，四个 SQL helper 已提供。

    batch 包含：source_id、expected_generation、embedding_config、operations、documents。
    operations 是你上一轮生成的动作列表；documents 为 document_id → 准备好的文档数据。
    准备数据含原文、清单、片段和向量；本函数不计算 Embedding，不打开新连接。

    执行要求：
    1. 所有 helper 必须在同一个 with connection.transaction(): 内调用。
    2. 事务中首先 lock_source(connection, source_id, expected_generation)，取得当前 generation。
       状态已变化会抛异常；让异常传出，不捕获后继续写。
    3. 依次执行 operations：
       REINDEX / METADATA_ONLY：replace_document(connection, source_id, batch['documents'][document_id])。
       DELETE：delete_document(connection, source_id, document_id)。
       UNCHANGED：不写文档；未知动作抛 ValueError。
    4. 统计每种动作数量。四个键 REINDEX/METADATA_ONLY/DELETE/UNCHANGED 均须出现，初始为 0。
    5. 有任何前三种动作时，事务结束前只调用一次
       advance_source(connection, source_id, batch['embedding_config'])，取得新 generation。
       全部 UNCHANGED（或空计划）则不推进 generation，保留 lock_source 返回值。
    6. 正常提交后返回 {"generation": generation, "counts": 四种动作计数字典}。

    异常由事务上下文管理器触发回滚；不要把每份文档放进独立事务。
    不修改 batch。代入 Java 可理解为一次带修订号校验的 @Transactional 批次。
    """
    counts = {
        "REINDEX": 0,
        "METADATA_ONLY": 0,
        "DELETE": 0,
        "UNCHANGED": 0,
    }
    source_id = batch["source_id"]
    with connection.transaction():
        generation = lock_source(
            connection,
            source_id,
            batch["expected_generation"],
        )
        for operation in batch["operations"]:
            action = operation["action"]
            document_id = operation["document_id"]
            if action == "REINDEX":
                replace_document(connection, source_id, batch["documents"][document_id])
                counts["REINDEX"] += 1
            elif action == "METADATA_ONLY":
                replace_document(connection, source_id, batch["documents"][document_id])
                counts["METADATA_ONLY"] += 1
            elif action == "DELETE":
                delete_document(connection, source_id, document_id)
                counts["DELETE"] += 1
            elif action == "UNCHANGED":
                counts["UNCHANGED"] += 1
            else:
                raise ValueError("未知动作")
        if counts["REINDEX"] > 0 or counts["METADATA_ONLY"] > 0 or counts["DELETE"] > 0:
            generation = advance_source(
                connection,
                source_id,
                batch["embedding_config"]
            )
    result = {
        "generation": generation,
        "counts": counts
    }
    return result
