"""助教提供：将原始制度转换为文档级清单，不调用 Embedding 模型。"""

import hashlib
import json
from pathlib import Path

from app.course.examples.foundations.retrieval import split_policy_document
from app.vector_index import current_embedding_config

LAB_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "document_sync_lab"


def fingerprint(value) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_document_manifest(document: dict, embedding_config: dict | None = None, *, chunks: list[dict] | None = None,
                            source_metadata: dict | None = None) -> dict:
    for key in ("id", "title", "version", "content"):
        if not isinstance(document.get(key), str) or not document[key].strip():
            raise ValueError(f"文档缺少非空字符串字段：{key}")
    departments = document.get("allowed_departments", [])
    if not isinstance(departments, list) or any(not isinstance(value, str) or not value for value in departments):
        raise ValueError("allowed_departments 应为非空部门 ID 的列表，可以是空列表")
    visibility = document.get("visibility", "public")
    if visibility not in ("public", "department") or (visibility == "department" and not departments):
        raise ValueError("访问元数据无效")
    if chunks is None:
        chunks = split_policy_document(document)
    if not chunks:
        raise ValueError("文档没有可用正文，不能将解析失败当作删除")
    if any(chunk["document_id"] != document["id"] for chunk in chunks):
        raise ValueError("片段所属文档不匹配")
    if embedding_config is None:
        embedding_config = current_embedding_config()
    metadata = {
        "title": document["title"], "version": document["version"],
        "source_sha256": fingerprint(document["content"]),
        "visibility": visibility, "allowed_departments": sorted(set(departments)),
    }
    if any(chunk.get("locator") for chunk in chunks):
        metadata["locators"] = [chunk.get("locator", {}) for chunk in chunks]
    if source_metadata is not None:
        metadata["source_metadata"] = source_metadata
    return {
        "id": document["id"], "version": document["version"],
        "vector_fingerprint": fingerprint({
            "texts": [chunk["content"] for chunk in chunks],
            "embedding": embedding_config,
        }),
        "metadata_fingerprint": fingerprint(metadata),
    }


def read_source_snapshot(name: str):
    # 读取/解析失败直接抛出；不返回空列表冒充来源已删除全部文档。
    snapshot = json.loads((LAB_DIRECTORY / name).read_text(encoding="utf-8"))
    if snapshot.get("complete") is not True or not snapshot.get("source_id"):
        raise ValueError("本课只接收指定知识源的完整快照")
    documents = snapshot["documents"]
    return snapshot, [build_document_manifest(document) for document in documents]
