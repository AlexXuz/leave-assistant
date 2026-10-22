"""助教提供的排序验收，使用明确的二维向量；无需下载模型或调用 API。"""

import copy

import numpy as np

from app.retrieval import rank_chunks


def main() -> int:
    chunks = [{"id": "side"}, {"id": "best"}, {"id": "second"}]
    vectors = np.array([[0.0, 1.0], [1.0, 0.0], [0.6, 0.8]], dtype=np.float32)
    query = np.array([1.0, 0.0], dtype=np.float32)
    before = copy.deepcopy(chunks)
    vectors_before = vectors.copy()
    try:
        results = rank_chunks(query, vectors, chunks, top_k=2)
        assert isinstance(results, list)
        assert [row["chunk"]["id"] for row in results] == ["best", "second"], "分数排序或片段对应关系不正确"
        assert all(set(row) == {"chunk", "score"} for row in results)
        assert all(type(row["score"]) is float for row in results), "score 应转为 Python float"
        assert np.allclose([row["score"] for row in results], [1.0, 0.6])
        assert chunks == before and np.array_equal(vectors, vectors_before), "不要修改传入数据"
        print("PASS: Top-2、分数与片段对应、数值类型、输入不变")

        all_results = rank_chunks(query, vectors, chunks, top_k=99)
        assert [row["chunk"]["id"] for row in all_results] == ["best", "second", "side"]
        tied = rank_chunks(query, np.array([[1.0, 0.0], [1.0, 0.0]]), [{"id": "first"}, {"id": "next"}], top_k=2)
        assert [row["chunk"]["id"] for row in tied] == ["first", "next"], "同分时应保留原顺序"
        assert rank_chunks(query, np.empty((0, 2)), [], top_k=2) == []
        try:
            rank_chunks(query, vectors, chunks, top_k=0)
        except ValueError:
            pass
        else:
            raise AssertionError("top_k 小于 1 应抛 ValueError")
        print("PASS: Top-K 大于片段数、同分顺序、空列表、非法 K")
    except NotImplementedError as error:
        print(f"待完成：{error}；未加载模型")
        return 2
    except (AssertionError, TypeError, KeyError) as error:
        print(f"FAIL: {error}；未加载模型")
        return 1
    print("排序验收通过；使用合成二维向量，零模型调用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
