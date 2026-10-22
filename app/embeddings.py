"""本地中文 Embedding 支持代码；模型加载与编码由助教提供。"""

import json
from functools import lru_cache
from pathlib import Path

MODEL_ID = "BAAI/bge-small-zh-v1.5"
MODEL_REVISION = "7999e1d3359715c523056ef9478215996d62a620"
MODEL_DIRECTORY = Path(__file__).resolve().parents[1] / ".models" / "bge-small-zh-v1.5"
MANIFEST_PATH = MODEL_DIRECTORY / "local_manifest.json"
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


@lru_cache(maxsize=1)
def load_embedding_model():
    if not MANIFEST_PATH.exists():
        raise RuntimeError("本地模型尚未准备完成；请先运行 python -m scripts.setup_local_embeddings")
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(str(MODEL_DIRECTORY), device="cpu", local_files_only=True)


def embed_documents(texts: list[str]):
    if not texts:
        raise ValueError("待编码文档列表不能为空")
    return load_embedding_model().encode(
        texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
    )


def embed_query(question: str):
    if not question.strip():
        raise ValueError("问题不能为空")
    return load_embedding_model().encode(
        QUERY_INSTRUCTION + question,
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False,
    )


def embedding_metadata() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {**manifest, "normalized": True, "query_instruction": QUERY_INSTRUCTION}
