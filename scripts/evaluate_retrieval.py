"""助教提供的 Top-K 对照实验：复用索引，每题只编码一次问题，不调用聊天 API。"""

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.embeddings import embed_query
from app.course.examples.foundations.retrieval import rank_chunks
from app.course.examples.foundations.retrieval_metrics import evaluate_evidence
from app.vector_index import load_index

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="比较必要证据 Recall@K 与全部证据命中率；不评回答")
    parser.add_argument("--top-k", type=int, nargs="+", default=[1, 2, 3, 4])
    args = parser.parse_args(argv)
    ks = sorted(set(args.top_k))
    if any(k < 1 for k in ks):
        parser.error("每个 K 必须至少为 1")
    # 未做作业时提前退出，不让模型加载掩盖待完成状态。
    try:
        evaluate_evidence([], ["readiness-probe"])
    except NotImplementedError as error:
        print(f"待完成：{error}；先运行 scripts.check_retrieval_metrics")
        return 2

    dataset_path = PROJECT_ROOT / "data" / "retrieval_cases.json"
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    cases = dataset["cases"]
    chunks, vectors, manifest = load_index()
    indexed_ids = {chunk["id"] for chunk in chunks}
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("评测集应非空且案例 ID 唯一")
    for case in cases:
        if not case["question"].strip() or not case["required_ids"]:
            raise ValueError(f"题目或必要证据为空：{case['id']}")
        if not set(case["required_ids"]) <= indexed_ids:
            raise ValueError(f"必要证据 ID 不在当前索引中：{case['id']}")

    rows = []
    print(f"读取已有索引；{len(cases)} 题，每题编码一次问题；不编码文档、不调用聊天模型。", flush=True)
    for case in cases:
        # 仅 question 进入 Embedding，人工标注不参与检索或改变排序。
        hits = rank_chunks(embed_query(case["question"]), vectors, chunks, max(ks))
        comparisons = {}
        for k in ks:
            selected = hits[:k]
            ids = [hit["chunk"]["id"] for hit in selected]
            comparisons[str(k)] = {
                **evaluate_evidence(ids, case["required_ids"]),
                "retrieved_ids": ids,
                "retrieved_count": len(selected),
                "context_chars": sum(len(hit["chunk"]["content"]) for hit in selected),
            }
        rows.append({**case, "ranked_hits": hits, "by_k": comparisons})
        brief = " | ".join(f"K={k}: {comparisons[str(k)]['evidence_recall']:.0%}" for k in ks)
        print(f"{case['id']}: {brief}", flush=True)

    summary = []
    print("\nK | 平均证据召回率 | 全部证据命中率 | 平均片段数 | 平均正文字符数")
    for k in ks:
        metrics = [row["by_k"][str(k)] for row in rows]
        count = len(metrics)
        item = {
            "top_k": k,
            "mean_evidence_recall": sum(m["evidence_recall"] for m in metrics) / count,
            "all_required_found_rate": sum(m["all_required_found"] for m in metrics) / count,
            "mean_retrieved_count": sum(m["retrieved_count"] for m in metrics) / count,
            "mean_context_chars": sum(m["context_chars"] for m in metrics) / count,
        }
        summary.append(item)
        print(f"{k} | {item['mean_evidence_recall']:.1%} | {item['all_required_found_rate']:.1%} | {item['mean_retrieved_count']:.1f} | {item['mean_context_chars']:.0f}")

    now = datetime.now(timezone(timedelta(hours=8)))
    record = {
        "run_time": now.isoformat(), "dataset_version": dataset["dataset_version"],
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "index_manifest": manifest, "case_count": len(cases), "top_ks": ks,
        "summary": summary, "cases": rows,
        "note": "公开小规模调试集；宏平均每题召回率。字符数不是 Token 数或实际费用。不评生成、语义引用正确性、拒答或未知问题泛化。",
    }
    directory = PROJECT_ROOT / "reports"
    directory.mkdir(exist_ok=True)
    path = directory / f"retrieval-eval-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告：{path}")
    print("这是必要证据检索结果，不是回答准确率；字符数只用于比较上下文规模。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
