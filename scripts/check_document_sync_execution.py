"""助教离线验收：模拟事务验证执行顺序、回滚、幂等和旧计划冲突。"""

import copy
import json
from contextlib import contextmanager
from unittest.mock import patch

from app import document_sync_execution as exercise
from app.document_sync_store import SourceRevisionConflict


class FakeConnection:
    def __init__(self):
        self.state = {"generation": 1, "documents": {"old": "v1", "keep": "same"}}
        self.active = False
        self.events = []

    @contextmanager
    def transaction(self):
        assert not self.active, "不要为每份文档另开事务"
        before = copy.deepcopy(self.state)
        self.active = True
        self.events.append("begin")
        try:
            yield
        except Exception:
            self.state = before
            self.events.append("rollback")
            raise
        else:
            self.events.append("commit")
        finally:
            self.active = False


def helpers(fail_on=None):
    def lock(connection, source_id, expected):
        assert connection.active and source_id == "fixture-source"
        assert connection.events == ["begin"], "lock_source 必须是事务内第一个 helper"
        connection.events.append("lock")
        if expected != connection.state["generation"]:
            raise SourceRevisionConflict("fixture conflict")
        return connection.state["generation"]

    def replace(connection, source_id, prepared):
        assert connection.active and source_id == "fixture-source"
        connection.state["documents"][prepared["id"]] = prepared["value"]
        connection.events.append("replace:" + prepared["id"])
        if prepared["id"] == fail_on:
            raise RuntimeError("模拟写入中途失败")

    def delete(connection, source_id, document_id):
        assert connection.active and source_id == "fixture-source"
        connection.state["documents"].pop(document_id, None)
        connection.events.append("delete:" + document_id)

    def advance(connection, source_id, config):
        assert connection.active and source_id == "fixture-source" and config == {"model": "fixture"}
        connection.state["generation"] += 1
        connection.events.append("advance")
        return connection.state["generation"]

    return {"lock_source": lock, "replace_document": replace, "delete_document": delete, "advance_source": advance}


def sample_batch():
    return {
        "source_id": "fixture-source", "expected_generation": 1, "embedding_config": {"model": "fixture"},
        "operations": [{"document_id": identifier, "action": action} for identifier, action in
                       (("new", "REINDEX"), ("meta", "METADATA_ONLY"), ("old", "DELETE"), ("keep", "UNCHANGED"))],
        "documents": {identifier: {"id": identifier, "value": "v2"} for identifier in ("new", "meta")},
    }


def check():
    batch = sample_batch()
    before = copy.deepcopy(batch)
    connection = FakeConnection()
    with patch.multiple(exercise, **helpers()):
        result = exercise.apply_sync_batch(connection, batch)
    assert result == {"generation": 2, "counts": {"REINDEX": 1, "METADATA_ONLY": 1, "DELETE": 1, "UNCHANGED": 1}}
    assert connection.state == {"generation": 2, "documents": {"keep": "same", "new": "v2", "meta": "v2"}}
    assert connection.events == ["begin", "lock", "replace:new", "replace:meta", "delete:old", "advance", "commit"]
    assert batch == before, "不应修改批次"
    # JSON 读取出的动作通常不是代码中的同一个字符串对象，比较应依据内容。
    decoded_batch = json.loads(json.dumps(batch))
    decoded_connection = FakeConnection()
    with patch.multiple(exercise, **helpers()):
        try:
            decoded_result = exercise.apply_sync_batch(decoded_connection, decoded_batch)
        except ValueError as error:
            raise AssertionError("JSON 读入的动作也应按内容匹配；字符串使用 == 比较") from error
    assert decoded_result == result, "JSON 读入的批次执行结果应相同"
    assert decoded_connection.state == connection.state
    assert decoded_connection.events == connection.events
    for operations in ([{"document_id": "keep", "action": "UNCHANGED"}], []):
        connection = FakeConnection()
        with patch.multiple(exercise, **helpers()):
            result = exercise.apply_sync_batch(connection, {**batch, "operations": operations})
        assert result["generation"] == 1 and connection.events == ["begin", "lock", "commit"]
        assert result["counts"] == {"REINDEX": 0, "METADATA_ONLY": 0, "DELETE": 0, "UNCHANGED": len(operations)}
    for mode, error_type in (("write_failure", RuntimeError), ("stale", SourceRevisionConflict), ("unknown", ValueError)):
        connection = FakeConnection()
        snapshot = copy.deepcopy(connection.state)
        value = copy.deepcopy(batch)
        if mode == "stale":
            value["expected_generation"] = 0
        if mode == "unknown":
            value["operations"][1]["action"] = "WRONG"
        with patch.multiple(exercise, **helpers(fail_on="meta" if mode == "write_failure" else None)):
            try:
                exercise.apply_sync_batch(connection, value)
            except error_type:
                pass
            else:
                raise AssertionError("异常必须传出以触发整批回滚")
        assert connection.state == snapshot, "中途写入或版本冲突后不应留下部分更新"
        assert connection.events[-1] == "rollback"


def main():
    try:
        check()
    except (AssertionError, NotImplementedError) as error:
        print(f"待完善：{error}；未连接数据库、未调用模型")
        return 1
    print("PASS：同一事务、修订号校验、动作执行、只推进一次、空批次及异常回滚通过")
    print("本轮使用模拟连接；真实 SQL、约束及并发效果在数据库验收阶段单独验证。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
