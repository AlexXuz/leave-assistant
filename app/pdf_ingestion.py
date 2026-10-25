"""Day 8 作业一：读取文本型 PDF，保留物理页码。"""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


from app.course.examples.foundations.pdf_ingestion import DocumentParseError  # Shared teaching interface.


def read_pdf_pages(path: str | Path) -> list[dict]:
    """本轮只实现此函数；open_pdf_reader 已处理打开、加密和零页问题。

    返回示例：
        [{'page': 1, 'text': '第1页提取的文字'},
         {'page': 2, 'text': '第2页提取的文字'}]

    1. reader = open_pdf_reader(path)。
    2. 按 reader.pages 顺序遍历，页码从 1 开始，为 PDF 物理页码。
       enumerate(reader.pages, start=1) 同时得到页码和 page 对象。
    3. page.extract_text() 返回字符串或 None；None 按空字符串处理。
       仅 strip() 去除本页文字两端空白，保留内部换行和文字顺序。
    4. 任一页结果为空，抛 DocumentParseError，错误消息包含页码。
       本课采取严格策略：空白页/扫描页均停止导入，留待人工确认或 OCR。
       不能跳过后重排页码，不能 except 后返回 [] 或已提取的前几页。
    5. 每页保存恰好 {'page': 页码, 'text': 提取文字}，返回整份列表。

    不合并全文、不切分片段、不删除页眉页脚、不用模型改写/补全正文。
    不硬编码两页或样例内容；不编码向量、不写数据库。
    PDF 内容流的提取顺序可能与视觉顺序不同，本课暂时保留原始提取结果。
    """
    raise NotImplementedError("请完成 read_pdf_pages；输入输出与验收见网页课程")


def open_pdf_reader(path: str | Path):
    """助教提供：失败不转换为空文档；文件不存在等 I/O 异常也直接传出。"""
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise DocumentParseError("本课暂不支持加密 PDF")
        if not reader.pages:
            raise DocumentParseError("PDF 没有页面，停止导入")
        return reader
    except PdfReadError as error:
        raise DocumentParseError("PDF 文件损坏或无法解析，停止导入") from error
