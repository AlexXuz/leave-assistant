"""助教验收：表头/单位/适用条件完整，章节范围与来源定位正确。"""

import argparse
import copy
import json

from app import docx_chunking as exercise
from app.docx_preparation import prepare_sample_docx, table_to_text
from app.pdf_ingestion import DocumentParseError


def check():
    sample = prepare_sample_docx()
    document, blocks = sample["document"], sample["blocks"]
    before = copy.deepcopy(sample)
    chunks = exercise.build_docx_chunks(document, blocks)
    assert sample == before, "不能修改输入块"
    assert [chunk["heading"] for chunk in chunks] == ["概述", "住宿标准", "申请与凭证"]
    expected_ranges = [(3, 3), (4, 7), (8, 11)]
    for chunk, (start, end) in zip(chunks, expected_ranges):
        assert set(chunk) == {"id", "document_id", "title", "version", "heading", "content", "locator"}
        assert chunk["id"] == f"{document['id']}:{document['version']}:b{start}-{end}"
        assert chunk["locator"] == {"kind": "docx", "source_file": document["source_file"],
                "source_sha256": document["source_sha256"], "section": chunk["heading"], "block_start": start, "block_end": end}
    lodging = chunks[1]["content"]
    assert lodging == "\n".join((document["title"], "住宿标准", "以下金额为每人每晚住宿报销上限。",
        "城市：北京和上海；住宿报销上限：520 元；计量单位：每人每晚",
        "城市：其他城市；住宿报销上限：380 元；计量单位：每人每晚",
        "超过上限的住宿，需要在预订前取得部门经理的书面批准。")), "表格应绑定表头，并保留同章节单位说明和超标审批条件"
    assert "办理事项：住宿报销；所需材料：对应的住宿发票和订单记录" in chunks[2]["content"]
    assert "每日餐费补贴" in chunks[2]["content"] and "520 元" not in chunks[2]["content"]
    print("PASS：真实 Word 的概述、两章分组、表头/单位/数值及表后条件完整。")

    fixture = {"id": "fixture", "title": "模拟制度", "version": "v3", "source_file": "fixture.docx", "source_sha256": "a" * 64}
    block_list = [
        {"kind": "paragraph", "block": 2, "style": "Heading 1", "text": "无正文章节"},
        {"kind": "paragraph", "block": 4, "style": "Heading 1", "text": "预算规则"},
        {"kind": "table", "block": 7, "rows": [["事项", "上限"], ["设备", "900 元"]]},
        {"kind": "paragraph", "block": 9, "style": "Normal", "text": "超过上限必须先审批。"},
        {"kind": "paragraph", "block": 12, "style": "Heading 1", "text": "补充规则"},
        {"kind": "paragraph", "block": 14, "style": "Heading 2", "text": "小标题保留"},
        {"kind": "paragraph", "block": 16, "style": "Normal", "text": "登记原始凭证。"},
    ]
    before = copy.deepcopy(block_list)
    result = exercise.build_docx_chunks(fixture, block_list)
    assert block_list == before
    assert [chunk["heading"] for chunk in result] == ["预算规则", "补充规则"]
    assert [(chunk["locator"]["block_start"], chunk["locator"]["block_end"]) for chunk in result] == [(4, 9), (12, 16)]
    assert result[0]["content"] == "模拟制度\n预算规则\n事项：设备；上限：900 元\n超过上限必须先审批。"
    assert result[1]["content"] == "模拟制度\n补充规则\n小标题保留\n登记原始凭证。"
    assert exercise.build_docx_chunks(fixture, []) == []
    assert exercise.build_docx_chunks(fixture, block_list[:1]) == []
    only_table = exercise.build_docx_chunks(fixture, [block_list[2]])
    assert only_table[0]["heading"] == "概述" and only_table[0]["locator"]["block_start"] == 7
    assert table_to_text([["项目", "金额"], ["A", ""]]) == "项目：A；金额：[空白]"
    for bad in ([["列", "列"], ["甲", "乙"]], [["列", ""], ["甲", "乙"]], [["A", "B"], ["甲"]], [["表头"]]):
        try:
            exercise.build_docx_chunks(fixture, [{"kind": "table", "block": 1, "rows": bad}])
        except DocumentParseError:
            pass
        else:
            raise AssertionError("表头/列数无法确定时必须拒绝，不丢列或猜测")
    try:
        exercise.build_docx_chunks(fixture, [{"kind": "paragraph", "block": 1, "style": "Normal", "text": "长正文" * 500}])
    except DocumentParseError:
        pass
    else:
        raise AssertionError("超长章节应明确拒绝，不能静默截断后声称完整")
    print("PASS：表格前无标题、非连续块号、空章节/空输入、下级标题保留与表格歧义拒绝。")
    return sample, chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()
    try:
        sample, chunks = check()
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    except (AssertionError, TypeError, KeyError) as error:
        print(f"FAIL：{error}")
        return 1
    if args.show:
        print(json.dumps({"profile_version": sample["profile_version"], "chunks": chunks}, ensure_ascii=False, indent=2))
    print("本脚本只验证章节切分；未编码/入库/调用聊天模型。真实问答由 scripts.ask_docx_rag 运行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
