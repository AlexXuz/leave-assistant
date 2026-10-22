"""助教提供：固定版本本地 Cross-Encoder 的加载与成对打分。"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL_ID = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
MODEL_REVISION = "1427fd652930e4ba29e8149678df786c240d8825"
WEIGHTS_SHA256 = "5daeca2481a76b5976a2bdc32f0a78532b6716da4f8cd3ff59460ef8d2f359b4"
MODEL_DIRECTORY = Path(__file__).resolve().parents[1] / ".models" / "mmarco-minilm-reranker"
MANIFEST_PATH = MODEL_DIRECTORY / "local_manifest.json"
MAX_LENGTH = 512
BATCH_SIZE = 8


def reranker_metadata():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError("本地重排模型尚未就绪；先运行 scripts.setup_local_reranker")
    metadata = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = {
        "model": MODEL_ID, "revision": MODEL_REVISION, "weights_sha256": WEIGHTS_SHA256,
        "max_length": MAX_LENGTH, "score_kind": "raw_logit", "device": "cpu",
    }
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError("本地重排模型清单与实验配置不一致")
    return metadata


@lru_cache(maxsize=1)
def load_reranker():
    reranker_metadata()
    with (MODEL_DIRECTORY / "model.safetensors").open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != WEIGHTS_SHA256:
            raise ValueError("重排模型权重校验失败")
    from sentence_transformers import CrossEncoder
    from torch.nn import Identity

    return CrossEncoder(
        str(MODEL_DIRECTORY), device="cpu", local_files_only=True,
        trust_remote_code=False, max_length=MAX_LENGTH, activation_fn=Identity(),
    )


def score_pairs(pairs: list[tuple[str, str]]) -> list[float]:
    if not pairs:
        return []
    scores = np.asarray(load_reranker().predict(
        pairs, batch_size=BATCH_SIZE, show_progress_bar=False, convert_to_numpy=True,
    ))
    if scores.shape != (len(pairs),) or not np.isfinite(scores).all():
        raise ValueError("重排模型应为每对文本返回一个有限分数")
    return [float(score) for score in scores]
