"""助教提供的事务内 SQL 操作。连接及批次准备在下一步运行器中管理。"""

import numpy as np
from pgvector import Vector
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from app.source_locations import validate_locator


class SourceRevisionConflict(ValueError):
    """执行前来源修订号已变化；调用方应重新读取状态并生成计划。"""


def require_transaction(connection):
    if connection.info.transaction_status != TransactionStatus.INTRANS:
        raise RuntimeError("文档同步操作必须位于同一个显式事务内")


def lock_source(connection, source_id: str, expected_generation: int) -> int:
    require_transaction(connection)
    row = connection.execute(
        "SELECT generation FROM leave_assistant_lab.synced_sources WHERE id = %s FOR UPDATE",
        (source_id,),
    ).fetchone()
    if row is None:
        raise ValueError("同步知识源尚未初始化")
    if row["generation"] != expected_generation:
        raise SourceRevisionConflict("知识源状态已变化，不能执行旧计划，请重新读取并规划")
    return int(row["generation"])


def replace_document(connection, source_id: str, prepared: dict):
    """准备好的新片段及向量替换该来源的一份文档；元数据更新也走此入口。"""
    require_transaction(connection)
    document = prepared["document"]
    manifest = prepared["manifest"]
    chunks = prepared["chunks"]
    vectors = np.asarray(prepared["vectors"], dtype=np.float32)
    if (not chunks or vectors.shape != (len(chunks), 512) or not np.isfinite(vectors).all() or
            not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)):
        raise ValueError("准备的片段和单位向量不完整或不匹配")
    if manifest["id"] != document["id"] or any(chunk["document_id"] != document["id"] for chunk in chunks):
        raise ValueError("准备数据的文档 ID 不一致")
    for chunk in chunks:
        validate_locator(chunk.get("locator", {}))
    connection.execute(
        "DELETE FROM leave_assistant_lab.synced_chunks WHERE source_id = %s AND document_id = %s",
        (source_id, document["id"]),
    )
    connection.execute(
        "INSERT INTO leave_assistant_lab.synced_documents "
        "(source_id,id,title,version,source_content,vector_fingerprint,metadata_fingerprint,visibility,allowed_departments) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (source_id,id) DO UPDATE SET "
        "title=EXCLUDED.title,version=EXCLUDED.version,source_content=EXCLUDED.source_content,"
        "vector_fingerprint=EXCLUDED.vector_fingerprint,metadata_fingerprint=EXCLUDED.metadata_fingerprint,"
        "visibility=EXCLUDED.visibility,allowed_departments=EXCLUDED.allowed_departments",
        (source_id, document["id"], document["title"], document["version"], document["content"],
         manifest["vector_fingerprint"], manifest["metadata_fingerprint"], document.get("visibility", "public"),
         sorted(set(document.get("allowed_departments", [])))),
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO leave_assistant_lab.synced_chunks "
            "(source_id,document_id,id,position,title,version,heading,content,locator,embedding) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [(source_id, document["id"], chunk["id"], index, chunk["title"], chunk["version"],
              chunk["heading"], chunk["content"], Jsonb(chunk.get("locator", {})), Vector(vectors[index]))
             for index, chunk in enumerate(chunks)],
        )


def delete_document(connection, source_id: str, document_id: str):
    require_transaction(connection)
    # 复合外键只级联删除这个来源的该文档片段。
    connection.execute(
        "DELETE FROM leave_assistant_lab.synced_documents WHERE source_id = %s AND id = %s",
        (source_id, document_id),
    )


def advance_source(connection, source_id: str, embedding_config: dict) -> int:
    require_transaction(connection)
    row = connection.execute(
        "UPDATE leave_assistant_lab.synced_sources SET generation = generation + 1, embedding_config = %s "
        "WHERE id = %s RETURNING generation",
        (Jsonb(embedding_config), source_id),
    ).fetchone()
    if row is None:
        raise ValueError("知识源不存在")
    return int(row["generation"])
