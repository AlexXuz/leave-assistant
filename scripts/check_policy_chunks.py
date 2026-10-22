"""助教提供的切分验收；不调用聊天或 Embedding 模型。

python -m scripts.check_policy_chunks
python -m scripts.check_policy_chunks --show
python -m scripts.check_policy_chunks --write
"""

import argparse
import copy
import json
from pathlib import Path

from app.retrieval import load_documents_for_chunking, split_policy_document

HEADINGS = {
    "leave-policy": ["申请时间", "年假审批", "知识范围"],
    "remote-policy": ["频率与审批", "固定现场日"],
    "travel-policy": ["住宿报销上限", "申请与凭证"],
}
KEYS = {"id", "document_id", "title", "version", "heading", "content"}
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "policy_chunks.json"


def check_document(document: dict, headings: list[str]) -> list[dict]:
    before = copy.deepcopy(document)
    chunks = split_policy_document(document)
    assert document == before, "不要修改输入文档"
    assert isinstance(chunks, list), "函数必须返回列表"
    assert [chunk["heading"] for chunk in chunks] == headings, "章节缺失、顺序错误或空章节未跳过"
    for index, chunk in enumerate(chunks, start=1):
        assert set(chunk) == KEYS, "每个片段应有约定的六个字段"
        assert all(isinstance(value, str) for value in chunk.values()), "片段各字段应为字符串"
        assert chunk["id"] == f"{document['id']}:{document['version']}:{index}", "片段 ID 格式不符合约定"
        assert chunk["document_id"] == document["id"], "原文档 ID 应保留"
        assert chunk["title"] == document["title"], "总标题应保留"
        assert chunk["version"] == document["version"], "版本应保留"
        prefix = f"{document['title']}\n{chunk['heading']}\n"
        assert chunk["content"].startswith(prefix), "片段正文前应包含总标题和章节标题"
        body = chunk["content"][len(prefix):]
        assert body and body == body.strip(), "正文应非空，并清理两端空白"
    return chunks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="制度切分本地验收，零模型调用")
    parser.add_argument("--show", action="store_true", help="打印片段全文")
    parser.add_argument("--write", action="store_true", help="验收通过后保存 data/policy_chunks.json")
    args = parser.parse_args(argv)
    try:
        chunks = []
        for document in load_documents_for_chunking():
            parts = check_document(document, HEADINGS[document["id"]])
            chunks.extend(parts)
            print(f"PASS: {document['id']}，{len(parts)} 个片段")
        assert len(chunks) == 7
        assert len({chunk["id"] for chunk in chunks}) == len(chunks), "片段 ID 不得重复"
        annual = next(chunk for chunk in chunks if chunk["heading"] == "年假审批")
        assert "不超过三天" in annual["content"] and "超过三天" in annual["content"]
        assert "直属主管和部门经理共同审批" in annual["content"], "审批条件和结论应在同一片段"
        # 简短合成输入检查连续空章节和无末尾换行，不把实际文档内容写进切分逻辑。
        fixture = {
            "id": "fixture", "title": "演示制度", "version": "test-v1",
            "content": "# 演示制度\n\n版本：test-v1\n\n## 空章节\n\n## 第一节\n第一行\n第二行\n\n## 最后一节\n最后一条规则",
        }
        fixture_chunks = check_document(fixture, ["第一节", "最后一节"])
        assert fixture_chunks[0]["content"] == "演示制度\n第一节\n第一行\n第二行"
        assert fixture_chunks[1]["content"] == "演示制度\n最后一节\n最后一条规则"
        print("PASS: 空章节跳过、内部换行与最后一节保留")
    except NotImplementedError as error:
        print(f"待完成：{error}；零模型调用")
        return 2
    except (AssertionError, KeyError, TypeError) as error:
        print(f"FAIL: {error}；零模型调用")
        return 1
    if args.show:
        print(json.dumps(chunks, ensure_ascii=False, indent=2))
    if args.write:
        OUTPUT_PATH.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已保存：{OUTPUT_PATH}")
    print("切分验收通过：3 份文档 → 7 个片段；零模型调用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
