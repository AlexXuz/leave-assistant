"""助教离线验收：同步计划及指纹含义，不连接数据库或调用模型。"""

import copy

from app.document_manifest import build_document_manifest
from app.document_sync import plan_document_sync


def manifest(identifier, vector, metadata):
    return {"id": identifier, "version": "v1", "vector_fingerprint": vector, "metadata_fingerprint": metadata}


def check():
    current = [manifest("meta", "a", "a"), manifest("changed", "b", "b"),
               manifest("deleted", "c", "c"), manifest("same", "d", "d")]
    incoming = [manifest("same", "d", "d"), manifest("meta", "a", "new"),
                manifest("new", "e", "e"), manifest("changed", "new", "b")]
    before = copy.deepcopy((current, incoming))
    expected = [
        {"document_id": "same", "action": "UNCHANGED"},
        {"document_id": "meta", "action": "METADATA_ONLY"},
        {"document_id": "new", "action": "REINDEX"},
        {"document_id": "changed", "action": "REINDEX"},
        {"document_id": "deleted", "action": "DELETE"},
    ]
    assert plan_document_sync(current, incoming, complete_snapshot=True) == expected, "动作、优先级或输出顺序不符"
    assert (current, incoming) == before, "不能修改输入清单"
    assert plan_document_sync([], [], complete_snapshot=True) == []
    assert plan_document_sync(current, [], complete_snapshot=True) == [
        {"document_id": value["id"], "action": "DELETE"} for value in current
    ]
    assert all(item["action"] == "REINDEX" for item in plan_document_sync([], incoming, complete_snapshot=True))
    for old, new, complete in ((current, [], False), (current + current[:1], incoming, True),
                               (current, incoming + incoming[:1], True)):
        try:
            plan_document_sync(old, new, complete_snapshot=complete)
        except ValueError:
            pass
        else:
            raise AssertionError("非完整快照或重复 ID 必须报错")
    # 核对助教指纹契约：版本标签及权限变更不应单独触发正文重新编码。
    document = {"id": "fixture", "title": "制度", "version": "v1", "content": "# 制度\n## 审批\n直属主管审批。"}
    config = {"model": "fixture-model", "weights_sha256": "one", "dimension": 512}
    old = build_document_manifest(document, config)
    versioned = build_document_manifest({**document, "version": "v2"}, config)
    assert old["vector_fingerprint"] == versioned["vector_fingerprint"]
    assert old["metadata_fingerprint"] != versioned["metadata_fingerprint"]
    secured = build_document_manifest({**document, "visibility": "department", "allowed_departments": ["hr"]}, config)
    assert old["vector_fingerprint"] == secured["vector_fingerprint"]
    assert old["metadata_fingerprint"] != secured["metadata_fingerprint"]
    new_model = build_document_manifest(document, {**config, "weights_sha256": "two"})
    assert old["vector_fingerprint"] != new_model["vector_fingerprint"]


def main():
    try:
        check()
    except (AssertionError, NotImplementedError) as error:
        print(f"待完善：{error}；未连接数据库、未调用模型")
        return 1
    print("PASS：新增/正文或模型变化/元数据变化/不变/删除分类及完整快照边界通过")
    print("只验同步计划，不代表数据库已更新；未连接数据库、未调用模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
