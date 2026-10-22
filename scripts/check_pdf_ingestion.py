"""助教验收：真实 PDF 按页读取与失败传播；不加载模型、不写知识库。"""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from pypdf import PdfWriter

from app import pdf_ingestion as exercise
from app.pdf_ingestion import DocumentParseError

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / "data/ingestion_lab/travel-policy.pdf"


def fake_reader(texts):
    pages = []
    for text in texts:
        page = MagicMock()
        page.extract_text.return_value = text
        pages.append(page)
    reader = MagicMock()
    reader.pages = pages
    return reader


def check():
    pages = exercise.read_pdf_pages(SAMPLE_PATH)
    assert len(pages) == 2, "样例应有两页，不合并全文或丢页"
    for number, page in enumerate(pages, 1):
        assert set(page) == {"page", "text"} and type(page["page"]) is int
        assert page["page"] == number and isinstance(page["text"], str)
        assert page["text"] and page["text"] == page["text"].strip()
    assert all(value in pages[0]["text"] for value in ("520", "380", "书面批准")), "第1页住宿规则提取不完整"
    assert all(value in pages[1]["text"] for value in ("住宿发票", "订单记录", "直属主管审批")), "第2页申请/凭证规则提取不完整"
    assert "住宿发票" not in pages[0]["text"] and "520" not in pages[1]["text"], "不要混合页面正文"
    print("PASS：真实中文 PDF 两页文字和物理页码正确。")

    reader = fake_reader(["  第一页甲\n乙  ", "\n第二页丙\n", " 第三页丁 "])
    with patch.object(exercise, "open_pdf_reader", return_value=reader):
        result = exercise.read_pdf_pages("fixture.pdf")
    assert result == [{"page": 1, "text": "第一页甲\n乙"}, {"page": 2, "text": "第二页丙"},
                      {"page": 3, "text": "第三页丁"}], "支持不同页数；只清理两端空白，不压平内部换行"
    for blank in (None, "", " \n\t "):
        reader = fake_reader(["已提取的第一页", blank, "后续页"])
        with patch.object(exercise, "open_pdf_reader", return_value=reader):
            try:
                exercise.read_pdf_pages("fixture.pdf")
            except DocumentParseError as error:
                assert "2" in str(error), "无文字页的错误需要指出物理页码"
            else:
                raise AssertionError("中间页无文字时必须停止，不能返回部分结果或跳过")
    failure = OSError("fixture extraction failure")
    reader = fake_reader(["第一页", "第二页"])
    reader.pages[1].extract_text.side_effect = failure
    with patch.object(exercise, "open_pdf_reader", return_value=reader):
        try:
            exercise.read_pdf_pages("fixture.pdf")
        except Exception as error:
            assert error is failure or error.__cause__ is failure, "保留真实提取错误或异常原因"
        else:
            raise AssertionError("提取异常不能吞掉后返回空列表或部分结果")
    print("PASS：不同页数、None/空白页、提取中途失败均按契约处理。")

    with TemporaryDirectory(prefix="day8-pdf-") as directory:
        base = Path(directory)
        for name, count, encrypted in (("blank.pdf", 1, False), ("zero.pdf", 0, False), ("encrypted.pdf", 1, True)):
            writer = PdfWriter()
            for _ in range(count):
                writer.add_blank_page(width=100, height=100)
            if encrypted:
                writer.encrypt("fixture-password")
            path = base / name
            writer.write(path)
            try:
                exercise.read_pdf_pages(path)
            except DocumentParseError:
                pass
            else:
                raise AssertionError(f"{name} 应明确失败，不能当成空文档成功返回")
        corrupt = base / "broken.pdf"
        corrupt.write_bytes(b"not a pdf")
        try:
            exercise.read_pdf_pages(corrupt)
        except DocumentParseError:
            pass
        else:
            raise AssertionError("损坏 PDF 应明确失败")
        try:
            exercise.read_pdf_pages(base / "missing.pdf")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("文件缺失应传出，不当成来源已删除")
    print("PASS：真实空白/零页/加密/损坏/缺失文件均未被当作有效空文档。")
    return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", action="store_true", help="验收通过后打印每页原始提取结果")
    args = parser.parse_args()
    try:
        pages = check()
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    except (AssertionError, TypeError, KeyError) as error:
        print(f"FAIL：{error}")
        return 1
    if args.show:
        for page in pages:
            print(f"\n--- PDF 第 {page['page']} 页 ---\n{page['text']}")
    print("解析验收通过；未切分、未入库、未调用 Embedding 或聊天模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
