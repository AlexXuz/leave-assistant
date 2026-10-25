"""助教运行器：真实 PostgreSQL 文档同步验收。默认只预览，--run 才写教学数据。"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

import numpy as np
from pgvector.psycopg import register_vector
from psycopg.errors import DivisionByZero

from app.course.examples.foundations import document_sync_execution as execution
from app.document_manifest import build_document_manifest, fingerprint, read_source_snapshot
from app.course.examples.foundations.document_sync import plan_document_sync
from app.document_sync_store import SourceRevisionConflict
from app.embeddings import embed_documents
from app.pgvector_store import PROJECT_ROOT, connect_database
from app.course.examples.foundations.retrieval import split_policy_document
from app.vector_index import current_embedding_config


def read_state(connection, source_id):
    """来源修订号、文档和向量必须从同一个一致快照读取。"""
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        source = connection.execute(
            "SELECT * FROM leave_assistant_lab.synced_sources WHERE id=%s", (source_id,)
        ).fetchone()
        if source is None:
            raise ValueError("教学知识源尚未初始化")
        documents = connection.execute(
            "SELECT * FROM leave_assistant_lab.synced_documents WHERE source_id=%s ORDER BY id", (source_id,)
        ).fetchall()
        chunks = connection.execute(
            "SELECT * FROM leave_assistant_lab.synced_chunks WHERE source_id=%s ORDER BY document_id,position",
            (source_id,),
        ).fetchall()
    # 从向量类型转成普通列表，便于完整状态比较及生成报告摘要。
    for chunk in chunks:
        chunk["embedding"] = chunk["embedding"].to_list()
    return {"source": source, "documents": documents, "chunks": chunks}


def prepare_batch(state, snapshot):
    """只在写事务外准备数据；返回批次和编码/复用数量，不更改数据库。"""
    if snapshot.get("complete") is not True or snapshot["source_id"] != state["source"]["id"]:
        raise ValueError("必须提供同一知识源的完整快照")
    config = current_embedding_config()
    incoming = [build_document_manifest(document, config) for document in snapshot["documents"]]
    current = [{key: document[key] for key in
                ("id", "version", "vector_fingerprint", "metadata_fingerprint")}
               for document in state["documents"]]
    operations = plan_document_sync(current, incoming, complete_snapshot=True)
    documents_by_id = {document["id"]: document for document in snapshot["documents"]}
    manifests_by_id = {manifest["id"]: manifest for manifest in incoming}
    prepared, stats = {}, {"encoded_chunks": 0, "reused_chunks": 0}
    for operation in operations:
        identifier, action = operation["document_id"], operation["action"]
        if action not in ("REINDEX", "METADATA_ONLY"):
            continue
        document = documents_by_id[identifier]
        chunks = split_policy_document(document)
        if action == "REINDEX":
            vectors = embed_documents([chunk["content"] for chunk in chunks])
            stats["encoded_chunks"] += len(chunks)
        else:
            old_chunks = [chunk for chunk in state["chunks"] if chunk["document_id"] == identifier]
            if ([chunk["position"] for chunk in old_chunks] != list(range(len(chunks))) or
                    [chunk["content"] for chunk in old_chunks] != [chunk["content"] for chunk in chunks] or
                    state["source"]["embedding_config"] != config):
                raise ValueError("旧片段正文、顺序或模型配置不匹配，不能复用向量")
            vectors = np.asarray([chunk["embedding"] for chunk in old_chunks], dtype=np.float32)
            stats["reused_chunks"] += len(chunks)
        prepared[identifier] = {"document": document, "manifest": manifests_by_id[identifier],
                                "chunks": chunks, "vectors": vectors}
    return {"source_id": snapshot["source_id"], "expected_generation": state["source"]["generation"],
            "embedding_config": config, "operations": operations, "documents": prepared}, stats


def original_collection_digest(connection):
    """对原问答表做只读摘要，确认实验前后内容相同。"""
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        collection = connection.execute(
            "SELECT * FROM leave_assistant_lab.collections WHERE name=%s", ("policy-dev",)
        ).fetchall()
        chunks = connection.execute(
            "SELECT collection,position,id,document_id,title,version,heading,content,embedding::text AS vector_text "
            "FROM leave_assistant_lab.policy_chunks WHERE collection=%s ORDER BY position", ("policy-dev",)
        ).fetchall()
    return fingerprint({"collection": collection, "chunks": chunks})


def run_lab():
    old, _ = read_source_snapshot("current.json")
    incoming, _ = read_source_snapshot("incoming.json")
    if old["source_id"] != incoming["source_id"]:
        raise ValueError("教学快照来源不一致")
    # 每次独立验收使用新来源，避免重置用户已有记录；报告中保留来源 ID。
    source_id = "day7-check-" + uuid4().hex
    old, incoming = {**old, "source_id": source_id}, {**incoming, "source_id": source_id}
    with connect_database() as connection:
        original_before = original_collection_digest(connection)
        with connection.transaction():
            connection.execute((PROJECT_ROOT / "infra/document_sync_schema.sql").read_text(encoding="utf-8"),
                               prepare=False)
            connection.execute("INSERT INTO leave_assistant_lab.synced_sources (id) VALUES (%s)", (source_id,))
        register_vector(connection)
        print(f"独立教学知识源：{source_id}", flush=True)
        empty = read_state(connection, source_id)
        seed_batch, seed_stats = prepare_batch(empty, old)
        execution.apply_sync_batch(connection, seed_batch)
        before = read_state(connection, source_id)
        assert before["source"]["generation"] == 1 and len(before["documents"]) == 4
        print(f"初始状态：generation=1，文档4份，片段{len(before['chunks'])}条。", flush=True)
        batch, stats = prepare_batch(before, incoming)
        for operation in batch["operations"]:
            print(f"{operation['document_id']}: {operation['action']}", flush=True)
        print(f"准备阶段：新编码{stats['encoded_chunks']}条，复用{stats['reused_chunks']}条。", flush=True)

        # 真正执行完删除，再由 PostgreSQL 抛出 SQL 错误，验证此前的替换和删除一起回滚。
        real_delete = execution.delete_document

        def delete_then_sql_error(conn, source, identifier):
            real_delete(conn, source, identifier)
            conn.execute("SELECT 1 / 0")

        with patch.object(execution, "delete_document", delete_then_sql_error):
            try:
                execution.apply_sync_batch(connection, batch)
            except DivisionByZero:
                pass
            else:
                raise AssertionError("故障注入未触发真实 SQL 异常")
        assert read_state(connection, source_id) == before, "整批回滚后状态应完全一致"
        print("PASS：替换和删除已执行后触发 SQL 错误，所有文档、向量及 generation 全部回滚。", flush=True)

        result = execution.apply_sync_batch(connection, batch)
        assert result == {"generation": 2, "counts":
                          {"REINDEX": 2, "METADATA_ONLY": 1, "DELETE": 1, "UNCHANGED": 1}}
        after = read_state(connection, source_id)
        assert {doc["id"] for doc in after["documents"]} == {doc["id"] for doc in incoming["documents"]}
        assert after["source"]["generation"] == 2
        assert after["source"]["embedding_config"] == batch["embedding_config"]
        for document in incoming["documents"]:
            stored = next(doc for doc in after["documents"] if doc["id"] == document["id"])
            manifest = build_document_manifest(document, batch["embedding_config"])
            assert stored["source_content"] == document["content"]
            assert all(stored[key] == manifest[key] for key in manifest)
            assert stored["title"] == document["title"]
            assert stored["visibility"] == document.get("visibility", "public")
            assert stored["allowed_departments"] == sorted(set(document.get("allowed_departments", [])))
            chunks = split_policy_document(document)
            rows = [chunk for chunk in after["chunks"] if chunk["document_id"] == document["id"]]
            assert [{key: row[key] for key in chunks[0]} for row in rows] == chunks
            if document["id"] in batch["documents"]:
                expected = np.asarray(batch["documents"][document["id"]]["vectors"], dtype=np.float32)
                assert np.array_equal(np.asarray([row["embedding"] for row in rows], dtype=np.float32), expected)
        assert not any(chunk["document_id"] == "travel-policy" for chunk in after["chunks"])
        old_ids = {chunk["id"] for chunk in before["chunks"] if chunk["document_id"] in ("leave-policy", "remote-policy")}
        assert old_ids.isdisjoint(chunk["id"] for chunk in after["chunks"]), "旧版本引用 ID 应消失"
        for identifier in ("leave-policy", "equipment-policy"):
            previous = [chunk["embedding"] for chunk in before["chunks"] if chunk["document_id"] == identifier]
            current = [chunk["embedding"] for chunk in after["chunks"] if chunk["document_id"] == identifier]
            assert previous == current, "元数据更新或未变化文档的向量应逐值不变"
        print("PASS：正式提交 generation=2；新版本替换、旧引用删除、差旅删除及向量复用正确。", flush=True)

        try:
            execution.apply_sync_batch(connection, batch)
        except SourceRevisionConflict:
            pass
        else:
            raise AssertionError("旧计划必须拒绝执行")
        assert read_state(connection, source_id) == after
        print("PASS：重放 expected_generation=1 的旧批次被拒绝，数据库保持不变。", flush=True)

        repeated_batch, repeated_stats = prepare_batch(after, incoming)
        assert repeated_stats == {"encoded_chunks": 0, "reused_chunks": 0}
        repeated_result = execution.apply_sync_batch(connection, repeated_batch)
        assert repeated_result == {"generation": 2, "counts":
                                   {"REINDEX": 0, "METADATA_ONLY": 0, "DELETE": 0, "UNCHANGED": 4}}
        assert read_state(connection, source_id) == after
        assert original_collection_digest(connection) == original_before, "原问答集合应保持不变"
        print("PASS：重新读取并规划后，4份均 UNCHANGED，无编码、无文档写入，generation仍为2。", flush=True)
        now = datetime.now(timezone(timedelta(hours=8)))
        record = {"run_time": now.isoformat(), "source_id": source_id, "database_verified": True,
                  "seed_preparation": seed_stats, "preparation": stats, "operations": batch["operations"],
                  "result": result, "repeated_result": repeated_result,
                  "before": {"generation": 1, "documents": len(before["documents"]), "chunks": len(before["chunks"])},
                  "after": {"generation": 2, "documents": len(after["documents"]), "chunks": len(after["chunks"])},
                  "checks": {"sql_failure_rollback": True, "metadata_vectors_unchanged": True,
                             "old_references_removed": True, "deleted_document_removed": True,
                             "stale_batch_rejected": True, "repeat_snapshot_noop": True,
                             "original_policy_dev_unchanged": True},
                  "limitations": "单进程真实数据库验收；未做两个并发写入者竞争行锁的实验，未调用聊天模型。"}
        path = PROJECT_ROOT / "reports" / f"document-sync-db-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告：{path}")
        print("调用了本地 Embedding，未调用 DeepSeek；教学数据已保留，原 policy-dev 内容未变。")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="在新建的独立教学来源执行真实数据库验收")
    args = parser.parse_args()
    if args.run:
        return run_lab()
    old, current = read_source_snapshot("current.json")
    new, incoming = read_source_snapshot("incoming.json")
    if old["source_id"] != new["source_id"]:
        raise ValueError("快照来源不一致")
    for operation in plan_document_sync(current, incoming, complete_snapshot=new["complete"]):
        print(f"{operation['document_id']}: {operation['action']}")
    print("仅预览，未连接数据库、未调用模型。加 --run 将新建独立教学来源并执行完整验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
