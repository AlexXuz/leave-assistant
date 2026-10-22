"""助教提供：下载约 470 MB 固定权重，验证本地 CPU 重排，不调用聊天 API。"""

import argparse
import hashlib
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from app.local_reranker import (
    BATCH_SIZE, MANIFEST_PATH, MAX_LENGTH, MODEL_DIRECTORY, MODEL_ID, MODEL_REVISION,
    WEIGHTS_SHA256,
)


def download_http_weights():
    """官方固定版本的分段 HTTP 回退；绕过失效的缓存重定向，不改变系统代理。"""
    total = 470592698
    block = 8 * 1024 * 1024
    directory = MODEL_DIRECTORY / ".http_parts"
    directory.mkdir(parents=True, exist_ok=True)
    destination = MODEL_DIRECTORY / "model.safetensors"
    if destination.exists():
        with destination.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() == WEIGHTS_SHA256:
                return
    url = f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/model.safetensors"

    def fetch(index):
        start = index * block
        end = min(start + block, total) - 1
        path = directory / f"{WEIGHTS_SHA256}.{index:03}.part"
        if path.exists() and path.stat().st_size == end - start + 1:
            return path
        for attempt in range(3):
            request = urllib.request.Request(
                url + "?download=true&cachebust=" + str(time.time_ns()),
                headers={"Range": f"bytes={start}-{end}"},
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{total}":
                        raise ValueError("下载响应的分段范围不匹配")
                    content = response.read(end - start + 2)
                if len(content) != end - start + 1:
                    raise ValueError("下载分段大小不匹配")
                path.write_bytes(content)
                return path
            except Exception:
                if attempt == 2:
                    raise
        raise RuntimeError("分段下载未完成")

    count = (total + block - 1) // block
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [pool.submit(fetch, index) for index in range(count)]
        for completed, task in enumerate(as_completed(tasks), 1):
            task.result()
            if completed % 4 == 0 or completed == count:
                print(f"权重分段：{completed}/{count}", flush=True)
    staged = MODEL_DIRECTORY / "model.safetensors.assembling"
    with staged.open("wb") as handle:
        for index in range(count):
            handle.write((directory / f"{WEIGHTS_SHA256}.{index:03}.part").read_bytes())
    with staged.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != WEIGHTS_SHA256:
            raise ValueError("完整下载文件校验失败")
    staged.replace(destination)
    for index in range(count):
        (directory / f"{WEIGHTS_SHA256}.{index:03}.part").unlink()


def main():
    parser = argparse.ArgumentParser(description="准备固定版本的本地多语言重排模型")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--http-weights", action="store_true", help="默认下载卡住时，使用官方分段 HTTP 下载权重")
    args = parser.parse_args()
    if not args.verify_only:
        from huggingface_hub import snapshot_download

        print(f"下载 {MODEL_ID}，revision={MODEL_REVISION}；权重约 470 MB。", flush=True)
        patterns = ["config.json", "tokenizer.json", "tokenizer_config.json",
                    "special_tokens_map.json", "sentencepiece.bpe.model"]
        if not args.http_weights:
            patterns.append("model.safetensors")
        snapshot_download(
            MODEL_ID, revision=MODEL_REVISION, local_dir=MODEL_DIRECTORY,
            allow_patterns=patterns,
            max_workers=2, token=False,
        )
        if args.http_weights:
            download_http_weights()
    print("文件已下载，开始权重校验及 CPU 推理。", flush=True)
    with (MODEL_DIRECTORY / "model.safetensors").open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != WEIGHTS_SHA256:
        raise ValueError("权重 SHA-256 不匹配")
    from sentence_transformers import CrossEncoder
    from torch.nn import Identity
    import numpy as np

    model = CrossEncoder(str(MODEL_DIRECTORY), device="cpu", local_files_only=True,
                         trust_remote_code=False, max_length=MAX_LENGTH, activation_fn=Identity())
    scores = np.asarray(model.predict(
        [("住宿报销要交哪些材料？", "报销住宿费用需要住宿发票和订单记录。"),
         ("住宿报销要交哪些材料？", "员工忘带门禁卡应向行政申请临时门禁。")],
        batch_size=BATCH_SIZE, show_progress_bar=False, convert_to_numpy=True,
    ))
    if scores.shape != (2,) or not np.isfinite(scores).all():
        raise ValueError("本地成对推理结果形状或数值无效")
    metadata = {
        "model": MODEL_ID, "revision": MODEL_REVISION, "weights_sha256": actual,
        "max_length": MAX_LENGTH, "score_kind": "raw_logit", "device": "cpu",
        "batch_size": BATCH_SIZE,
    }
    MANIFEST_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(f"本地推理成功，返回 {len(scores)} 个有限分数；后续仅从本地加载。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
