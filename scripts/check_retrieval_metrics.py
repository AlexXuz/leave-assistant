"""助教提供的纯 Python 验收：无模型调用，无文件修改。"""

from app.retrieval_metrics import evaluate_evidence


def main() -> int:
    examples = [
        (["remote", "other"], ["leave", "remote"], 0.5, False, ["leave"]),
        (["remote", "leave", "extra"], ["leave", "remote"], 1.0, True, []),
        ([], ["b", "a"], 0.0, False, ["a", "b"]),
        (["extra"], ["a"], 0.0, False, ["a"]),
        (["a", "a"], ["a", "a", "b"], 0.5, False, ["b"]),
    ]
    try:
        for retrieved, required, recall, complete, missing in examples:
            before = (retrieved.copy(), required.copy())
            result = evaluate_evidence(retrieved, required)
            assert set(result) == {"evidence_recall", "all_required_found", "missing_ids"}, "返回字段不符合约定"
            assert type(result["evidence_recall"]) is float, "evidence_recall 应为 float"
            assert type(result["all_required_found"]) is bool, "all_required_found 应为 bool"
            assert result == {"evidence_recall": recall, "all_required_found": complete, "missing_ids": missing}, f"输入 {before} 的结果不正确：{result}"
            assert (retrieved, required) == before, "不要修改输入列表"
        try:
            evaluate_evidence(["a"], [])
        except ValueError:
            pass
        else:
            raise AssertionError("必要证据为空时应抛 ValueError")
    except NotImplementedError as error:
        print(f"待完成：{error}；未加载模型")
        return 2
    except (AssertionError, TypeError, KeyError, ValueError) as error:
        print(f"FAIL: {error}；未加载模型")
        return 1
    print("PASS: 部分/全部/零召回、去重、缺失列表顺序、空标注边界及输入不变")
    print("指标函数验收通过；未加载 Embedding，未调用聊天模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
