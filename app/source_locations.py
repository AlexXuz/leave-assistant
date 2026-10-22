"""助教提供：定位字段校验及授权命中的定位补充。"""

from copy import deepcopy


def validate_locator(locator):
    if not isinstance(locator, dict):
        raise ValueError("locator 必须是对象；没有来源位置时使用空对象")
    if not locator:
        return
    common = {"kind", "source_file", "source_sha256"}
    fields = {"pdf": {"page", "start", "end"}, "docx": {"section", "block_start", "block_end"}}
    kind = locator.get("kind")
    if not isinstance(kind, str) or kind not in fields or set(locator) != common | fields[kind]:
        raise ValueError("非空 locator 应为完整的 PDF 或 DOCX 定位")
    if not isinstance(locator["source_file"], str) or not locator["source_file"].strip():
        raise ValueError("定位缺少文件标识")
    digest = locator["source_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("文件指纹格式不正确")
    if kind == "pdf":
        if any(type(locator[key]) is not int for key in ("page", "start", "end")):
            raise ValueError("页码及字符范围应为整数")
        if locator["page"] < 1 or not 0 <= locator["start"] < locator["end"]:
            raise ValueError("页码及字符范围无效")
    else:
        if not isinstance(locator["section"], str) or not locator["section"].strip():
            raise ValueError("Word 定位缺少章节名称")
        if any(type(locator[key]) is not int for key in ("block_start", "block_end")):
            raise ValueError("正文块范围应为整数")
        if not 1 <= locator["block_start"] <= locator["block_end"]:
            raise ValueError("正文块范围无效")


def attach_chunk_locators(connection, source_id: str, hits: list[dict]) -> list[dict]:
    """在同一个只读一致快照中补充本次授权命中的定位，不查询额外文档。"""
    if not hits:
        return []
    identifiers = [hit["chunk"]["id"] for hit in hits]
    rows = connection.execute(
        "SELECT id,locator FROM leave_assistant_lab.synced_chunks WHERE source_id=%s AND id=ANY(%s)",
        (source_id, identifiers),
    ).fetchall()
    by_id = {row["id"]: row["locator"] for row in rows}
    if set(by_id) != set(identifiers):
        raise ValueError("授权命中的定位记录不完整，停止组装引用")
    results = deepcopy(hits)
    for hit in results:
        locator = by_id[hit["chunk"]["id"]]
        validate_locator(locator)
        # 无定位旧片段保持原来六字段结构，兼容 Day 7 的返回契约。
        if locator:
            hit["chunk"]["locator"] = deepcopy(locator)
    return results
