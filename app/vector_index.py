"""助教提供的单文件向量索引读写与一致性检查；不调用 Embedding/聊天模型。"""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from app.embeddings import embedding_metadata
from app.course.examples.foundations.policy_qa import load_policy_documents
from app.course.examples.foundations.retrieval import load_documents_for_chunking, split_policy_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = PROJECT_ROOT / "data" / "policy_chunks.json"
INDEX_PATH = PROJECT_ROOT / "data" / "indexes" / "policy-index.npz"
CONFIG_KEYS = (
    "model", "revision", "weights_sha256", "dimension", "max_seq_length",
    "normalized", "query_instruction",
)


class IndexValidationError(ValueError):
    """索引不完整、不匹配或已过期；需要检查原因并重建。"""


def _json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value) -> str:
    return hashlib.sha256(_json_text(value).encode("utf-8")).hexdigest()


def current_embedding_config() -> dict:
    metadata = embedding_metadata()
    return {key: metadata[key] for key in CONFIG_KEYS}


def source_fingerprint() -> str:
    # 包含实际正文及文档集合，正文修改但忘记更新版本也会被发现。
    return _fingerprint(load_policy_documents())


def load_current_chunks() -> list[dict]:
    """入库前确认已保存片段与当前原文一致，不自动切分或生成向量。"""
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    fresh_chunks = []
    for document in load_documents_for_chunking():
        fresh_chunks.extend(split_policy_document(document))
    if not chunks or _fingerprint(chunks) != _fingerprint(fresh_chunks):
        raise IndexValidationError("片段与当前制度不一致；先运行 scripts.check_policy_chunks --write")
    return chunks


def _validate_vectors(chunks: list[dict], vectors, config: dict) -> np.ndarray:
    array = np.ascontiguousarray(vectors, dtype=np.float32)
    if not chunks or array.shape != (len(chunks), config["dimension"]):
        raise IndexValidationError("向量应为二维数组，行数等于片段数，列数等于模型维度")
    if not np.isfinite(array).all():
        raise IndexValidationError("向量包含非有限数值")
    if not np.allclose(np.linalg.norm(array, axis=1), 1.0, atol=1e-5):
        raise IndexValidationError("当前索引约定存储单位长度向量")
    if len({chunk["id"] for chunk in chunks}) != len(chunks):
        raise IndexValidationError("片段 ID 不得重复")
    return array


def save_index(chunks: list[dict], vectors) -> dict:
    """保存同一批次的片段、向量、清单，返回清单 dict。"""
    if _fingerprint(chunks) != _fingerprint(load_current_chunks()):
        raise IndexValidationError("待保存片段不是当前已验收的片段")
    config = current_embedding_config()
    vectors = _validate_vectors(chunks, vectors, config)
    manifest = {
        "format_version": 1,
        "built_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "embedding": config,
        "chunk_count": len(chunks),
        "ordered_chunk_ids": [chunk["id"] for chunk in chunks],
        "chunks_sha256": _fingerprint(chunks),
        "sources_sha256": source_fingerprint(),
        "vectors_sha256": hashlib.sha256(vectors.tobytes()).hexdigest(),
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=INDEX_PATH.parent, suffix=".tmp", delete=False) as file:
            temporary_path = Path(file.name)
            np.savez_compressed(
                file, vectors=vectors,
                chunks_json=np.array(_json_text(chunks)),
                manifest_json=np.array(_json_text(manifest)),
            )
        # 单个文件替换，避免查询读到不同批次的片段与向量。
        os.replace(temporary_path, INDEX_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return manifest


def load_index() -> tuple[list[dict], np.ndarray, dict]:
    """只读取和校验已有索引，返回 (chunks, vectors, manifest)；不自动重建。"""
    if not INDEX_PATH.exists():
        raise FileNotFoundError("索引尚不存在；先运行 python -m scripts.build_policy_index")
    with np.load(INDEX_PATH, allow_pickle=False) as archive:
        chunks = json.loads(archive["chunks_json"].item())
        manifest = json.loads(archive["manifest_json"].item())
        vectors = archive["vectors"].copy()
    if manifest.get("format_version") != 1:
        raise IndexValidationError("不支持的索引格式")
    if manifest["embedding"] != current_embedding_config():
        raise IndexValidationError("Embedding 模型或编码配置已变化，请重建索引")
    vectors = _validate_vectors(chunks, vectors, manifest["embedding"])
    if manifest["chunk_count"] != len(chunks):
        raise IndexValidationError("片段数量与清单不一致")
    if manifest["ordered_chunk_ids"] != [chunk["id"] for chunk in chunks]:
        raise IndexValidationError("片段顺序与向量行映射不一致")
    if manifest["chunks_sha256"] != _fingerprint(chunks):
        raise IndexValidationError("索引中的片段内容发生变化")
    if manifest["vectors_sha256"] != hashlib.sha256(vectors.tobytes()).hexdigest():
        raise IndexValidationError("索引向量数据发生变化")
    if manifest["sources_sha256"] != source_fingerprint():
        raise IndexValidationError("制度正文或文档集合已变化；重新切分并重建索引")
    current_chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    if manifest["chunks_sha256"] != _fingerprint(current_chunks):
        raise IndexValidationError("片段文件已变化，请重建索引")
    return chunks, vectors, manifest
