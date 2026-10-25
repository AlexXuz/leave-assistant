"""助教提供：按需准备独立的授权制度知识源，结束时清理自己的教学数据。"""

from contextlib import contextmanager

from pgvector.psycopg import register_vector

from app.document_manifest import build_document_manifest
from app.course.examples.foundations.document_sync import plan_document_sync
from app.course.examples.foundations.document_sync_execution import apply_sync_batch
from app.embeddings import embed_documents, load_embedding_model
from app.pgvector_store import PROJECT_ROOT, connect_database
from app.course.examples.foundations.retrieval import load_documents_for_chunking, split_policy_document
from app.vector_index import current_embedding_config


@contextmanager
def teaching_policy_source(source_id, record):
    """只供运行器调用；不在余额查询分支建立数据库依赖。"""
    config = current_embedding_config()
    prepared = {}
    for original in load_documents_for_chunking():
        document = {**original, "visibility": "department", "allowed_departments": ["engineering"]}
        chunks = split_policy_document(document)
        tokenized = load_embedding_model().tokenizer([c["content"] for c in chunks],
                                                    add_special_tokens=True, truncation=False)
        if any(len(tokens) > config["max_seq_length"] for tokens in tokenized["input_ids"]):
            raise ValueError("教学片段超过编码容量，需要先调整切分")
        prepared[document["id"]] = {
            "document": document, "chunks": chunks,
            "manifest": build_document_manifest(document, config, chunks=chunks),
            "vectors": embed_documents([c["content"] for c in chunks]),
        }
    record.update(real_embedding=True, embedding=config,
                  documents=[item["document"] for item in prepared.values()],
                  chunk_count=sum(len(item["chunks"]) for item in prepared.values()))
    with connect_database() as connection:
        with connection.transaction():
            connection.execute((PROJECT_ROOT / "infra/document_sync_schema.sql").read_text(encoding="utf-8"), prepare=False)
        register_vector(connection)
        created = False
        try:
            with connection.transaction():
                connection.execute("INSERT INTO leave_assistant_lab.synced_sources (id) VALUES (%s)", (source_id,))
            created = True
            record["teaching_source_created"] = True
            batch = {"source_id": source_id, "expected_generation": 0, "embedding_config": config,
                     "operations": plan_document_sync([], [item["manifest"] for item in prepared.values()], complete_snapshot=True),
                     "documents": prepared}
            record["sync_result"] = apply_sync_batch(connection, batch)
            record["database_prepared"] = True
            print(f"教学制度已编码并写入独立来源：{len(prepared)}份/{record['chunk_count']}个片段。", flush=True)
            yield source_id
        finally:
            if created:
                with connection.transaction():
                    connection.execute("DELETE FROM leave_assistant_lab.synced_documents WHERE source_id=%s", (source_id,))
                    connection.execute("DELETE FROM leave_assistant_lab.synced_sources WHERE id=%s", (source_id,))
                record["teaching_data_cleaned"] = connection.execute(
                    "SELECT count(*) AS count FROM leave_assistant_lab.synced_sources WHERE id=%s", (source_id,)
                ).fetchone()["count"] == 0
