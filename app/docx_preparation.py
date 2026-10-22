"""助教提供：表格转带标签的事实、短章节片段与原文定位。"""

import hashlib
import json
from pathlib import Path

from app.docx_ingestion import read_docx_blocks
from app.pdf_ingestion import DocumentParseError

DIRECTORY = Path(__file__).resolve().parents[1] / "data/ingestion_lab"
MAX_SECTION_CHARS = 400


def prepare_sample_docx(profile_path=None):
    profile_path = Path(profile_path).resolve() if profile_path is not None else DIRECTORY / "docx_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    document = profile["document"]
    path = profile_path.parent / document["source_file"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    raw_blocks = read_docx_blocks(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise DocumentParseError("文件在读取期间发生变化，请重试")
    ignored = set(profile["remove_paragraph_texts"])
    # 标题稍后统一放入片段前缀；只删除本样例登记的元数据行，概述和审批条件均保留。
    blocks = [block for block in raw_blocks if not (
        block["kind"] == "paragraph" and
        (block["text"] in ignored or (block["style"] == "Title" and block["text"] == document["title"])))]
    return {"document": {**document, "source_sha256": digest}, "raw_blocks": raw_blocks,
            "blocks": blocks, "profile_version": profile["profile_version"]}


def validate_blocks(blocks):
    previous = 0
    for block in blocks:
        number = block["block"]
        if type(number) is not int or number <= previous:
            raise DocumentParseError("正文块号应为严格递增的原文位置")
        previous = number
        if block["kind"] == "paragraph":
            if not isinstance(block["text"], str) or not block["text"].strip():
                raise DocumentParseError("输入包含空白正文块")
        elif block["kind"] == "table":
            continue
        else:
            raise DocumentParseError("未知正文块类型")


def table_to_text(rows: list[list[str]]) -> str:
    """本课约定首行为表头；逐行绑定标签，避免 zip 静默截断不齐的列。"""
    if len(rows) < 2 or not rows[0]:
        raise DocumentParseError("表格必须有一行表头和至少一行数据")
    headers = [header.strip() for header in rows[0]]
    if any(not header for header in headers) or len(set(headers)) != len(headers):
        raise DocumentParseError("表头缺失或重复，无法明确关联数值")
    records = []
    for row in rows[1:]:
        if len(row) != len(headers):
            raise DocumentParseError("数据行与表头列数不一致，不能猜测列对应关系")
        records.append("；".join(f"{header}：{value.strip() or '[空白]'}" for header, value in zip(headers, row)))
    return "\n".join(records)


def make_section_chunk(document: dict, section: dict) -> dict:
    """统一片段字段由助教提供；section 的分组与范围由学生实现。"""
    body = "\n".join(section["parts"])
    content = "\n".join((document["title"], section["heading"], body))
    if len(content) > MAX_SECTION_CHARS:
        raise DocumentParseError("章节超过本课短章节上限，需更细切分；不能静默截断")
    start, end = section["block_start"], section["block_end"]
    return {"id": f"{document['id']}:{document['version']}:b{start}-{end}",
            "document_id": document["id"], "title": document["title"], "version": document["version"],
            "heading": section["heading"], "content": content,
            "locator": {"kind": "docx", "source_file": document["source_file"],
                        "source_sha256": document["source_sha256"], "section": section["heading"],
                        "block_start": start, "block_end": end}}
