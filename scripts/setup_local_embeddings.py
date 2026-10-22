"""下载固定版本的公开 Embedding 模型，验证 CPU 推理；不调用聊天 API。"""

import argparse
import hashlib
import json
import os

# 首次下载容忍较慢网络；不改变用户的全局配置。
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")
# 此环境的 Xet 下载出现响应解码错误，默认改用普通 HTTP 下载。
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from app.embeddings import MANIFEST_PATH, MODEL_DIRECTORY, MODEL_ID, MODEL_REVISION


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并验证本地 Embedding 模型")
    parser.add_argument("--verify-only", action="store_true", help="只验证已经下载的本地文件")
    args = parser.parse_args()
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer

    if not args.verify_only:
        print(f"准备下载 {MODEL_ID}，revision={MODEL_REVISION}", flush=True)
        snapshot_download(
            repo_id=MODEL_ID, revision=MODEL_REVISION, local_dir=MODEL_DIRECTORY,
            allow_patterns=[
                "config.json", "config_sentence_transformers.json", "modules.json",
                "sentence_bert_config.json", "special_tokens_map.json", "tokenizer.json",
                "tokenizer_config.json", "vocab.txt", "1_Pooling/config.json", "model.safetensors",
            ],
            max_workers=2,
        )
    print("文件下载完成，开始验证本地 CPU 推理。", flush=True)
    model = SentenceTransformer(str(MODEL_DIRECTORY), device="cpu", local_files_only=True)
    vectors = model.encode(["连续年假审批", "上海住宿标准"], normalize_embeddings=True)
    import numpy as np
    assert vectors.ndim == 2 and vectors.shape[0] == 2
    assert np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
    with (MODEL_DIRECTORY / "model.safetensors").open("rb") as weights:
        weights_sha256 = hashlib.file_digest(weights, "sha256").hexdigest()
    manifest = {
        "model": MODEL_ID, "revision": MODEL_REVISION,
        "dimension": int(vectors.shape[1]), "max_seq_length": model.max_seq_length,
        "device": "cpu",
        "weights_sha256": weights_sha256,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("本地模型已就绪；后续编码仅使用本地文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
