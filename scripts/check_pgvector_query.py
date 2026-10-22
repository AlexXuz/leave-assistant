"""纯本地接口验收：模拟数据库返回，不验证 PostgreSQL 实际执行 SQL。"""

import copy

import numpy as np

from app.pgvector_retrieval import search_pgvector
from app.pgvector_store import CHUNK_FIELDS, COLLECTION_NAME


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, parameters):
        self.calls.append((sql, parameters))
        return self

    def fetchall(self):
        return copy.deepcopy(self.rows)


def main() -> int:
    chunks = [
        {"id": "first", "document_id": "doc-1", "title": "标题一", "version": "v1", "heading": "章节一", "content": "正文一"},
        {"id": "second", "document_id": "doc-2", "title": "标题二", "version": "v1", "heading": "章节二", "content": "正文二"},
    ]
    rows = [{**chunk, "score": score} for chunk, score in zip(chunks, [0.75, 0.5])]
    connection = FakeConnection(rows)
    query = np.eye(1, 512, dtype=np.float32)[0]
    before = query.copy()
    try:
        results = search_pgvector(connection, query, 2)
        assert results == [{"chunk": chunk, "score": score} for chunk, score in zip(chunks, [0.75, 0.5])], "片段字段、分数或 SQL 返回顺序发生变化"
        assert all(set(row["chunk"]) == set(CHUNK_FIELDS) and type(row["score"]) is float for row in results), "保留六个片段字段，score 为 float"
        assert len(connection.calls) == 1, "一次检索只执行一次查询"
        sql, parameters = connection.calls[0]
        assert "%s" in sql and len(parameters) == 4, "使用参数化 SQL，传四个参数"
        assert parameters[1] == COLLECTION_NAME and parameters[3] == 2, "集合或 K 参数不正确"
        assert np.array_equal(parameters[0].to_numpy(), query) and np.array_equal(parameters[2].to_numpy(), query), "两个向量参数都应由原问题向量适配"
        assert np.array_equal(query, before), "不要修改输入向量"
        assert search_pgvector(FakeConnection([]), query, 2) == [], "空结果返回空列表"
        for invalid in [0, -1]:
            no_query = FakeConnection([])
            try:
                search_pgvector(no_query, query, invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("K 小于 1 应抛 ValueError")
            assert not no_query.calls, "非法 K 应先拒绝，不访问数据库"
    except NotImplementedError as error:
        print(f"待完成：{error}；未连接数据库、未调用模型")
        return 2
    except (AssertionError, TypeError, KeyError, AttributeError, ValueError) as error:
        print(f"FAIL: {error}；未连接数据库、未调用模型")
        return 1
    print("PASS: 参数适配、查询调用、结果结构与顺序、空结果、非法 K、输入不变")
    print("仅模拟数据库返回的接口验收通过；真实 SQL 与检索一致性仍需数据库验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
