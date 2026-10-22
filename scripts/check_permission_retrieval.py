"""真实 PostgreSQL 权限验收：固定单位向量，不加载模型；教学数据最终回滚。"""

import math
from uuid import uuid4

import numpy as np
from pgvector.psycopg import register_vector

from app.permission_retrieval import search_visible_chunks
from app.document_manifest import build_document_manifest
from app.document_sync_store import replace_document
from app.pgvector_store import CHUNK_FIELDS, PROJECT_ROOT, connect_database
from app.retrieval import split_policy_document


class RollbackFixture(Exception):
    """验收成功后也回滚临时数据。"""


class NoQueryConnection:
    def execute(self, *args, **kwargs):
        raise AssertionError("非法 top_k 应在执行 SQL 前拒绝")


def make_fixture(identifier, score, visibility, departments, *, title=None):
    title = title or identifier
    document = {"id": identifier, "title": title, "version": "permission-v1",
                "content": f"# {title}\n\n## 教学记录\n{title}的权限测试正文。",
                "visibility": visibility, "allowed_departments": departments}
    # 空部门限制文档用于验证异常 ACL 状态也不会泄露，数据库允许此状态。
    manifest_document = document
    if visibility == "department" and not departments:
        manifest_document = {**document, "allowed_departments": ["fixture-initial"]}
    manifest = build_document_manifest(manifest_document, {"fixture": "no-model"})
    vector = np.zeros(512, dtype=np.float32)
    vector[0], vector[1] = score, math.sqrt(1 - score * score)
    return {"document": document, "manifest": manifest, "chunks": split_policy_document(document),
            "vectors": vector.reshape(1, -1)}


def check():
    query = np.zeros(512, dtype=np.float32)
    query[0] = 1
    for invalid in (0, -1):
        try:
            search_visible_chunks(NoQueryConnection(), query, "fixture", (), invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("top_k < 1 必须抛 ValueError")
    source = "day7-acl-" + uuid4().hex
    other_source = source + "-other"
    fixtures = [make_fixture("finance", 1.0, "department", ["finance"]),
                make_fixture("empty-acl", .99, "department", []),
                make_fixture("engineering", .80, "department", ["engineering"]),
                make_fixture("shared", .75, "department", ["engineering", "finance"]),
                make_fixture("public", .70, "public", [])]
    with connect_database() as connection:
        with connection.transaction():
            connection.execute((PROJECT_ROOT / "infra/document_sync_schema.sql").read_text(encoding="utf-8"),
                               prepare=False)
        register_vector(connection)
        try:
            with connection.transaction():
                for identifier in (source, other_source):
                    connection.execute("INSERT INTO leave_assistant_lab.synced_sources (id) VALUES (%s)",
                                       (identifier,))
                for fixture in fixtures:
                    replace_document(connection, source, fixture)
                # 另一来源有同名 public 文档，能发现遗漏复合 JOIN 条件/来源范围的错误。
                replace_document(connection, other_source,
                                 make_fixture("finance", 1.0, "public", [], title="其他来源的同名文档"))
                source_count_before = connection.execute(
                    "SELECT count(*) AS count FROM leave_assistant_lab.synced_chunks WHERE source_id=%s", (source,)
                ).fetchone()["count"]
                cases = [("研发部门", ("engineering",), 2, ["engineering", "shared"]),
                         ("财务部门", ("finance",), 2, ["finance", "shared"]),
                         ("无部门权限", (), 2, ["public"]),
                         ("不在授权列表的部门", ("sales",), 2, ["public"]),
                         ("多个部门", ("engineering", "finance"), 3, ["finance", "engineering", "shared"]),
                         ("部门参数含 SQL 字符", ("finance') OR true --",), 2, ["public"]),
                         ("K 大于可见数量", ("engineering",), 20, ["engineering", "shared", "public"]),
                         ("不存在的来源", (), 2, [])]
                for label, departments, top_k, expected_ids in cases:
                    before = query.copy()
                    hits = search_visible_chunks(connection, query, source + "-missing" if not expected_ids else source,
                                                 departments, top_k)
                    assert [hit["chunk"]["document_id"] for hit in hits] == expected_ids, f"{label}：授权范围或排名不正确"
                    expected_scores = {fixture["document"]["id"]: float(fixture["vectors"][0, 0]) for fixture in fixtures}
                    for hit in hits:
                        assert set(hit) == {"chunk", "score"} and set(hit["chunk"]) == set(CHUNK_FIELDS)
                        assert type(hit["score"]) is float
                        assert math.isclose(hit["score"], expected_scores[hit["chunk"]["document_id"]], abs_tol=1e-6)
                        assert hit["chunk"]["title"] != "其他来源的同名文档", "不能串到其他知识源"
                    assert np.array_equal(query, before), "不能修改问题向量"
                    print(f"PASS：{label} -> {expected_ids}")
                source_count_after = connection.execute(
                    "SELECT count(*) AS count FROM leave_assistant_lab.synced_chunks WHERE source_id=%s", (source,)
                ).fetchone()["count"]
                assert source_count_before == source_count_after == 5
                raise RollbackFixture()
        except RollbackFixture:
            pass
        assert connection.execute("SELECT count(*) AS count FROM leave_assistant_lab.synced_sources WHERE id=ANY(%s)",
                                  ([source, other_source],)).fetchone()["count"] == 0
    print("PASS：真实 SQL 的部门可见范围、过滤后 Top-K、空权限、来源隔离及参数绑定通过。")
    print("固定向量；未加载 Embedding、未调用聊天模型；临时教学数据已回滚。")


def main():
    try:
        check()
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    except AssertionError as error:
        print(f"FAIL：{error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
