"""助教验收：引用 ID 映射；--database 验证 PDF 定位入库到授权检索的传递。"""

import argparse
import copy
import json
import math
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import numpy as np
from pgvector.psycopg import register_vector

from app import permission_service as service
from app import source_citations as exercise
from app.document_manifest import build_document_manifest
from app.document_sync import plan_document_sync
from app.document_sync_execution import apply_sync_batch
from app.located_chunking import split_located_pages
from app.permission_rag import prepare_authorized_rag_request
from app.permission_service import TrustedAccessContext
from app.pdf_preparation import prepare_sample_pdf
from app.pgvector_store import PROJECT_ROOT, connect_database
from app.policy_qa import parse_policy_answer
from scripts.check_permission_retrieval import make_fixture


def expected_citation(chunk):
    return {"chunk_id": chunk["id"], "document_id": chunk["document_id"], "title": chunk["title"],
            "version": chunk["version"], "locator": chunk.get("locator")}


def check_mapping():
    base = {"document_id": "fixture", "title": "模拟资料", "version": "v1", "heading": "位置", "content": "正文"}
    first = {**base, "id": "opaque-id-a", "locator": {"kind": "pdf", "source_file": "fixture.pdf",
             "source_sha256": "a" * 64, "page": 17, "start": 0, "end": 2}}
    second = {**base, "id": "opaque-id-b", "locator": {**first["locator"], "page": 21}}
    legacy = {**base, "id": "legacy:v1:1"}
    hits = [{"chunk": chunk, "score": .8} for chunk in (first, second, legacy)]
    ids = [second["id"], first["id"], second["id"], legacy["id"]]
    before = copy.deepcopy((ids, hits))
    assert exercise.resolve_citations(ids, hits) == [expected_citation(chunk) for chunk in (second, first, legacy)], \
        "按模型引用顺序去重，从命中映射完整定位；旧片段无定位返回 None"
    assert (ids, hits) == before, "不修改输入"
    assert exercise.resolve_citations([], hits) == []
    assert exercise.resolve_citations([], []) == []
    for values, candidates in ((["not-retrieved"], hits), ([first["id"], "not-retrieved"], hits),
                               ([first["id"]], []), ([first["id"]], hits + [hits[0]])):
        try:
            exercise.resolve_citations(values, candidates)
        except ValueError:
            pass
        else:
            raise AssertionError("未知 ID 或重复命中 ID 必须拒绝，不允许忽略或补查")
    print("PASS：引用顺序、去重、未知 ID 拒绝、定位映射及旧片段兼容。")


def prepare_pdf_fixture():
    sample = prepare_sample_pdf()
    chunks = split_located_pages(sample["document"], sample["pages"])
    document = {**sample["document"], "content": "\n\n".join(page["text"] for page in sample["pages"]),
                "visibility": "department", "allowed_departments": ["engineering"]}
    config = {"fixture": "fixed-vector"}
    metadata = {"cleaning_profile": sample["profile_version"], "chunking": {"max_chars": 200, "overlap": 30}}
    manifest = build_document_manifest(document, config, chunks=chunks, source_metadata=metadata)
    changed = copy.deepcopy(chunks)
    changed[0]["locator"]["page"] += 10
    moved = build_document_manifest(document, config, chunks=changed, source_metadata=metadata)
    assert manifest["vector_fingerprint"] == moved["vector_fingerprint"]
    assert manifest["metadata_fingerprint"] != moved["metadata_fingerprint"]
    assert plan_document_sync([manifest], [moved], complete_snapshot=True)[0]["action"] == "METADATA_ONLY"
    # 仅在内存中模拟位置改变，验证指纹语义，不把虚构页码写进实际 PDF 记录。
    vectors = np.zeros((len(chunks), 512), dtype=np.float32)
    for index in range(len(chunks)):
        score = .8 - index * .05
        vectors[index, 0], vectors[index, 1] = score, math.sqrt(1 - score * score)
    return {"document": document, "manifest": manifest, "chunks": chunks, "vectors": vectors}, config


def check_database(show=False):
    prepared_pdf, config = prepare_pdf_fixture()
    source = "day8-citation-" + uuid4().hex
    secret = make_fixture("finance-secret", 1.0, "department", ["finance"])
    query = np.eye(1, 512, dtype=np.float32)[0]
    with connect_database() as connection:
        with connection.transaction():
            connection.execute((PROJECT_ROOT / "infra/document_sync_schema.sql").read_text(encoding="utf-8"), prepare=False)
        register_vector(connection)
        try:
            with connection.transaction():
                connection.execute("INSERT INTO leave_assistant_lab.synced_sources (id) VALUES (%s)", (source,))
            documents = [prepared_pdf, secret]
            batch = {"source_id": source, "expected_generation": 0, "embedding_config": config,
                     "operations": plan_document_sync([], [item["manifest"] for item in documents], complete_snapshot=True),
                     "documents": {item["document"]["id"]: item for item in documents}}
            result = apply_sync_batch(connection, batch)
            assert result["generation"] == 1
            stored = connection.execute(
                "SELECT id,locator FROM leave_assistant_lab.synced_chunks WHERE source_id=%s AND document_id=%s",
                (source, prepared_pdf["document"]["id"]),
            ).fetchall()
            assert {row["id"]: row["locator"] for row in stored} == {chunk["id"]: chunk["locator"] for chunk in prepared_pdf["chunks"]}
            print("PASS：PDF 片段通过同步执行器入库，JSONB 定位逐条一致。")

            with patch.object(service, "embed_query", return_value=query), \
                 patch.object(service, "current_embedding_config", return_value=config):
                access = TrustedAccessContext("fixture-user", (source,), ("engineering",))
                prepared = prepare_authorized_rag_request("查询差旅制度及凭证要求。", source, access, 3)
                hits = prepared["retrieved_chunks"]
                assert [hit["chunk"]["id"] for hit in hits] == [chunk["id"] for chunk in prepared_pdf["chunks"]]
                assert all(hit["chunk"]["locator"] == chunk["locator"] for hit, chunk in zip(hits, prepared_pdf["chunks"]))
                assert "finance-secret" not in "\n".join(message["content"] for message in prepared["messages"])
                # 固定模型响应只测试 sources 的映射，不把它冒充真实模型回答。
                ids = [hits[-1]["chunk"]["id"], hits[0]["chunk"]["id"], hits[-1]["chunk"]["id"]]
                answer = parse_policy_answer(json.dumps({"answer": "固定响应，仅验证引用映射。", "canAnswer": True,
                                                         "sources": ids}, ensure_ascii=False), prepared["documents"])
                citations = exercise.resolve_citations(answer["sources"], hits)
                assert citations == [expected_citation(hits[index]["chunk"]) for index in (-1, 0)]
                try:
                    exercise.resolve_citations([secret["chunks"][0]["id"]], hits)
                except ValueError:
                    pass
                else:
                    raise AssertionError("数据库存在但本次无权命中的片段不可用于引用")
                visitor = prepare_authorized_rag_request("查询制度", source, TrustedAccessContext("fixture-visitor", (source,), ()), 2)
                assert visitor["retrieved_chunks"] == [] and visitor["documents"] == []
            print("PASS：真实只读事务内授权检索保留定位，固定响应映射为第2页、第1页引用。")
            print("PASS：库中存在但无权命中的 ID 被拒绝，无部门用户没有受限证据。")
            now = datetime.now(timezone(timedelta(hours=8)))
            report = {"run_time": now.isoformat(), "source_id": source, "database_verified": True,
                      "real_embedding": False, "real_chat_model": False, "citations": citations,
                      "checks": {"locator_round_trip": True, "authorized_retrieval": True,
                                 "citation_mapping": True, "unretrieved_id_rejected": True},
                      "note": "固定向量及固定模型响应；未评估生成质量、真实 Embedding 排名或文件打开授权。"}
        finally:
            # 仅清理本次新建的随机教学来源；先删文档级联片段，再删来源。
            with connection.transaction():
                connection.execute("DELETE FROM leave_assistant_lab.synced_documents WHERE source_id=%s", (source,))
                connection.execute("DELETE FROM leave_assistant_lab.synced_sources WHERE id=%s", (source,))
        assert connection.execute("SELECT count(*) AS count FROM leave_assistant_lab.synced_sources WHERE id=%s",
                                  (source,)).fetchone()["count"] == 0
    report["teaching_data_cleaned"] = True
    path = PROJECT_ROOT / "reports" / f"source-citations-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if show:
        print(json.dumps(citations, ensure_ascii=False, indent=2))
    print(f"报告：{path}")
    print("临时教学来源已清理；新增的 locator 列保留，原问答集合未参与写入。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", action="store_true")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()
    try:
        check_mapping()
        if args.database:
            check_database(args.show)
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    except (AssertionError, ValueError, TypeError, KeyError) as error:
        print(f"FAIL：{error}")
        return 1
    if not args.database:
        print("引用映射离线验收通过；加 --database 验证入库、授权检索与引用定位。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
