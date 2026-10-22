"""助教提供的排名融合验收：不加载任何模型、不连接数据库。"""

import copy
import math

from app.hybrid_retrieval import fuse_rrf


def hit(identifier, score):
    return {"chunk": {"id": identifier, "content": f"正文 {identifier}"}, "score": score}


def check():
    routes = [[hit("A", 0.8), hit("B", 0.7)], [hit("C", 20), hit("B", 10)]]
    original = copy.deepcopy(routes)
    result = fuse_rrf(routes, top_k=3)
    assert [row["chunk"]["id"] for row in result] == ["B", "A", "C"], "跨路应按 ID 合并、累计并稳定排序"
    assert math.isclose(result[0]["score"], 2 / 62), "排名从 1 开始，B 在两路都排第二"
    assert math.isclose(result[1]["score"], 1 / 61)
    assert all(isinstance(row["score"], float) for row in result)
    assert routes == original, "不能修改原检索分数或输入列表"
    rescaled = copy.deepcopy(routes)
    for route in rescaled:
        for row in route:
            row["score"] = -12345.0
    assert fuse_rrf(rescaled, top_k=3) == result, "RRF 只使用排名，不使用原始分数"
    assert fuse_rrf(routes, top_k=1) == result[:1]
    assert fuse_rrf([], top_k=2) == [] and fuse_rrf([[], []]) == []
    duplicated = [[hit("A", 4), hit("A", 3), hit("B", 2)], []]
    single = fuse_rrf(duplicated, top_k=9, rank_constant=10)
    assert [row["chunk"]["id"] for row in single] == ["A", "B"], "同一路重复 ID 不能重复加分"
    assert math.isclose(single[0]["score"], 1 / 11)
    assert math.isclose(single[1]["score"], 1 / 13), "重复项之后仍保留原列表名次"
    for kwargs in ({"top_k": 0}, {"rank_constant": 0}):
        try:
            fuse_rrf([], **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("非法 K 或排名常数应抛 ValueError")


def main():
    try:
        check()
    except (NotImplementedError, AssertionError) as error:
        print(f"待完善：{error}；未加载模型、未连接数据库")
        return 1
    print("PASS：排名累加、跨路去重、稳定排序、原分数不参与、输入不变和参数边界通过")
    print("未加载模型、未连接数据库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
