"""助教验收：片段完整覆盖、重叠、页码及来源定位；无模型或数据库调用。"""

import argparse
import copy
import json

from app import located_chunking as exercise
from app.pdf_preparation import clean_pdf_pages, prepare_sample_pdf


def verify(document, pages, chunks, max_chars, overlap):
    cursor = 0
    for page in pages:
        start, ordinal = 0, 1
        while True:
            assert cursor < len(chunks), "片段不足，可能漏掉页尾或某一页"
            chunk = chunks[cursor]
            location = chunk["locator"]
            assert set(chunk) == {"id", "document_id", "title", "version", "heading", "content", "locator"}
            assert location == {"kind": "pdf", "source_file": document["source_file"],
                                "source_sha256": document["source_sha256"], "page": page["page"],
                                "start": start, "end": min(start + max_chars, len(page["text"]))}
            assert chunk["id"] == f"{document['id']}:{document['version']}:p{page['page']}:c{ordinal}"
            assert chunk["document_id"] == document["id"] and chunk["version"] == document["version"]
            assert chunk["title"] == document["title"] and chunk["heading"] == f"第{page['page']}页"
            assert chunk["content"] == document["title"] + "\n" + page["text"][start:location["end"]], "正文应能按来源位置精确还原"
            cursor += 1
            if location["end"] == len(page["text"]):
                break
            start = location["end"] - overlap
            ordinal += 1
    assert cursor == len(chunks), "出现多余片段，检查是否重复切了已覆盖的页尾"
    assert len({chunk["id"] for chunk in chunks}) == len(chunks)


def check():
    sample = prepare_sample_pdf()
    document, pages = sample["document"], sample["pages"]
    before = copy.deepcopy(sample)
    chunks = exercise.split_located_pages(document, pages)
    verify(document, pages, chunks, 200, 30)
    assert sample == before, "不能修改输入"
    assert all("虚构教学资料" not in page["text"] and "阅读示例：" not in page["text"] for page in pages)
    assert "520" in pages[0]["text"] and "380" in pages[0]["text"]
    assert "书面批准" in pages[0]["text"] and "订单记录" in pages[1]["text"]
    print("PASS：真实 PDF 清理后切分，正文、页码、文件指纹与字符位置对应。")
    fixture = {"id": "fixture", "title": "模拟文档", "version": "v9", "source_file": "fixture.pdf", "source_sha256": "fixture-sha"}
    for size, overlap in ((6, 2), (6, 0), (6, 5), (20, 3), (1, 0)):
        for length in (1, 6, 7, 10, 11, 13):
            # 页码不连续，防止按列表序号伪造位置；第一行含空格/换行，防止窗口被 strip。
            pages = [{"page": 2, "text": ("甲 乙\n丙丁戊己庚辛壬癸" * 2)[:length]},
                     {"page": 5, "text": "另一页尾部"}]
            before = copy.deepcopy(pages)
            result = exercise.split_located_pages(fixture, pages, size, overlap)
            verify(fixture, pages, result, size, overlap)
            assert pages == before
    assert exercise.split_located_pages(fixture, []) == []
    for size, overlap in ((0, 0), (-1, 0), (5, -1), (5, 5), (5, 6)):
        try:
            exercise.split_located_pages(fixture, [], size, overlap)
        except ValueError:
            pass
        else:
            raise AssertionError("窗口参数无效时先抛 ValueError，即使页面为空也不能忽略")
    for text in ("", " \n "):
        try:
            exercise.split_located_pages(fixture, [{"page": 3, "text": text}])
        except ValueError:
            pass
        else:
            raise AssertionError("空白页面需要明确拒绝")
    assert clean_pdf_pages([{"page": 4, "text": "页眉\n审批要求不能删除\n520 元"}], ["页眉"]) == [
        {"page": 4, "text": "审批要求不能删除\n520 元"}]
    print("PASS：不同窗口/重叠、尾部完整覆盖、非连续页码、空输入与错误参数。")
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
    except (AssertionError, ValueError, TypeError, KeyError) as error:
        print(f"FAIL：{error}")
        return 1
    if args.show:
        print(json.dumps({"profile_version": sample["profile_version"], "chunks": chunks}, ensure_ascii=False, indent=2))
    print("本轮只切分并保留定位；尚未写库、编码或调用聊天模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
