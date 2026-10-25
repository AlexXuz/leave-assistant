"""助教提供：受限样例的清理配置、原始结果及文件指纹，不调用模型。"""

import hashlib
import json
from pathlib import Path

from app.course.examples.foundations.pdf_ingestion import DocumentParseError, read_pdf_pages

DIRECTORY = Path(__file__).resolve().parents[1] / "data/ingestion_lab"


def clean_pdf_pages(pages: list[dict], remove_lines: list[str]) -> list[dict]:
    """仅移除配置明确列出的整行，不以含数字/审批等泛化规则删除内容。"""
    ignored = set(remove_lines)
    results = []
    for page in pages:
        text = "\n".join(line.strip() for line in page["text"].splitlines()
                         if line.strip() and line.strip() not in ignored).strip()
        if not text:
            raise DocumentParseError(f"第{page['page']}页清理后无正文，需要人工检查")
        results.append({"page": page["page"], "text": text})
    return results


def prepare_sample_pdf():
    profile = json.loads((DIRECTORY / "pdf_profile.json").read_text(encoding="utf-8"))
    path = DIRECTORY / profile["document"]["source_file"]
    source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    raw_pages = read_pdf_pages(path)
    # 发现本地文件在读取期间变化，停止而非绑定错误版本的来源指纹。
    if hashlib.sha256(path.read_bytes()).hexdigest() != source_hash:
        raise DocumentParseError("文件在读取期间发生变化，请重试")
    return {"document": {**profile["document"], "source_sha256": source_hash},
            "profile_version": profile["profile_version"], "raw_pages": raw_pages,
            "pages": clean_pdf_pages(raw_pages, profile["remove_lines"])}
