"""助教提供：重排接线验收，使用固定评分器，不调用真实模型。"""

import copy
import json
from unittest.mock import Mock

import numpy as np

from app.reranking import rerank_candidates


def check():
    candidates = [
        {"chunk": {"id": str(i), "content": f"正文{i}"}, "score": 1.0 / i}
        for i in range(1, 6)
    ]
    before = copy.deepcopy(candidates)
    scorer = Mock(return_value=[-2.0, 0.1, 0.1, -1.0, 4.0])
    result = rerank_candidates("问题", candidates, scorer, top_k=3)
    scorer.assert_called_once_with([("问题", f"正文{i}") for i in range(1, 6)])
    assert [hit["chunk"]["id"] for hit in result] == ["5", "2", "3"], "应给全部候选打分，同分稳定排序"
    assert result[0] == {"chunk": candidates[4]["chunk"], "score": 4.0, "retrieval_score": 0.2}
    assert all(isinstance(hit["score"], float) and isinstance(hit["retrieval_score"], float) for hit in result)
    assert candidates == before, "不应修改候选及检索分数"
    # 真实本地模型可能返回 NumPy 标量，普通 Python float 样例覆盖不到 JSON 序列化问题。
    numpy_candidates = copy.deepcopy(candidates)
    for hit in numpy_candidates:
        hit["score"] = np.float32(hit["score"])
    numpy_before = copy.deepcopy(numpy_candidates)
    numpy_scorer = Mock(return_value=np.array([-2.0, 0.1, 0.1, -1.0, 4.0], dtype=np.float32))
    numpy_result = rerank_candidates("问题", numpy_candidates, numpy_scorer, top_k=2)
    assert all(type(hit["score"]) is float for hit in numpy_result), "新评分应通过 float(...) 转为 Python float"
    assert all(type(hit["retrieval_score"]) is float for hit in numpy_result), "原检索分数也应通过 float(...) 转为 Python float"
    json.dumps(numpy_result, ensure_ascii=False)
    assert numpy_candidates == numpy_before, "数值类型转换也不能修改原候选"
    scorer = Mock()
    assert rerank_candidates("问题", [], scorer) == []
    scorer.assert_not_called()
    for scores in ([1.0], [1.0] * 6):
        try:
            rerank_candidates("问题", candidates, lambda pairs: scores)
        except ValueError:
            pass
        else:
            raise AssertionError("评分条数不符必须明确报错")
    try:
        rerank_candidates("问题", [], scorer, top_k=0)
    except ValueError:
        pass
    else:
        raise AssertionError("非法 K 必须先检查")
    scorer.assert_not_called()


def main():
    try:
        check()
    except (NotImplementedError, AssertionError) as error:
        print(f"待完善：{error}；未加载模型、未连接数据库")
        return 1
    print("PASS：成对输入、全部候选一次评分、分数关联、稳定排序、原分数保留和参数边界通过")
    print("本验收使用固定评分器，只证明接线正确，不证明真实模型能改善检索。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
