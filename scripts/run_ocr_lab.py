"""助教提供：单页图片 OCR 对照。只读本地图片，保留原始识别行，不写知识库。"""

import argparse
from datetime import datetime
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time

from PIL import Image
import rapidocr_onnxruntime
from rapidocr_onnxruntime import RapidOCR

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/ingestion_lab/ocr"
EXPECTED = {"北京/上海金额": "520", "其他城市金额": "380", "单位": "每人每晚",
            "审批时点": "预订前", "审批人": "部门经理", "审批形式": "书面批准"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recognize(engine, case):
    path = DIRECTORY / f"travel-page1-{case}.png"
    fingerprint = digest(path)
    with Image.open(path) as image:
        width, height = image.size
    started = time.perf_counter()
    result, stage_seconds = engine(str(path))
    if digest(path) != fingerprint:
        raise ValueError("图片在识别期间变化，请重新运行")
    # 分数、文本和坐标原样关联；保留引擎返回的次序，不按文本内容重排。
    lines = [{"line": index, "text": text, "score": float(score), "polygon": box}
             for index, (box, text, score) in enumerate(result or [], 1)]
    text = "\n".join(line["text"] for line in lines)
    compact = "".join(text.split())
    return {"case": case, "image_file": path.relative_to(ROOT).as_posix(), "image_sha256": fingerprint,
            "width": width, "height": height, "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "stage_seconds": stage_seconds, "status": "recognized" if lines else "no_text",
            "lines": lines, "text": text,
            "review_hint_lines": [line["line"] for line in lines if line["score"] < 0.90],
            "keyword_presence_only": {key: value in compact for key, value in EXPECTED.items()},
            "human_review": "pending", "eligible_for_ingestion": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("clear", "small", "tiny", "both", "all"), default="all")
    args = parser.parse_args()
    provenance = json.loads((DIRECTORY / "manifest.json").read_text(encoding="utf-8"))
    if digest(ROOT / provenance["source_pdf"]) != provenance["source_pdf_sha256"]:
        raise ValueError("原PDF与图片生成记录不一致，需要重新渲染实验图")
    for item in provenance["images"].values():
        if digest(DIRECTORY / item["file"]) != item["sha256"]:
            raise ValueError("实验图与生成记录不一致，不能套用原图核对标准")
    # 固定 CPU 线程数；0.5为引擎文本输出过滤阈值，0.9仅用于提示人工看哪些行。
    engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
    model_directory = Path(rapidocr_onnxruntime.__file__).parent / "models"
    record = {"run_time": datetime.now().astimezone().isoformat(),
              "engine": "rapidocr-onnxruntime", "engine_version": version("rapidocr-onnxruntime"),
              "runtime_version": version("onnxruntime"),
              "models_sha256": {path.name: digest(path) for path in sorted(model_directory.glob("*.onnx"))},
              "engine_text_score_threshold": 0.5, "review_hint_threshold": 0.90,
              "source_pdf": "data/ingestion_lab/travel-policy.pdf", "source_page": 1,
              "source_pdf_sha256": digest(ROOT / "data/ingestion_lab/travel-policy.pdf"),
              "fixture_provenance": provenance,
              "sample_note": "均为同一PDF第1页的渲染图；clear=170dpi，small=最长边680像素，tiny=320像素。不是实拍扫描。",
              "limitations": "关键词出现不证明城市/金额对应正确；置信分数不是业务事实正确率。输出仅实验，未接入同步或引用。",
              "real_local_ocr": True, "chat_model_called": False, "database_written": False, "cases": []}
    cases = ("clear", "small", "tiny") if args.case == "all" else ("clear", "small") if args.case == "both" else (args.case,)
    for case in cases:
        item = recognize(engine, case)
        record["cases"].append(item)
        print(f"\n[{case}] {item['width']}x{item['height']}，{len(item['lines'])}行，{item['elapsed_ms']}ms")
        for line in item["lines"]:
            hint = " [复核提示]" if line["score"] < 0.90 else ""
            print(f"  L{line['line']:02d} score={line['score']:.3f}{hint} {line['text']}")
        print("关键词存在检查（不等于语义正确）：", item["keyword_presence_only"])
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = ROOT / "reports" / f"ocr-lab-{stamp}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告：{path}")
    print("各图都需人工对照，分数高也不能跳过金额/单位/条件复核。未入库，未调用聊天模型。")
    return 0 if all(item["lines"] for item in record["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
