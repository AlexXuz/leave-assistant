"""助教提供：重放固定 RRF 候选，比较真实 Cross-Encoder 前后，不重新召回。"""

import argparse
import copy
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

from app.local_reranker import load_reranker, reranker_metadata, score_pairs
from app.course.examples.foundations.reranking import rerank_candidates
from scripts.retrieval_lab import ROOT, measurement, read_fixture

BASELINE = ROOT / "reports" / "retrieval-lab-v2-20261018-112435-358398.json"


def load_baseline(path):
    raw = path.read_bytes()
    source = json.loads(raw)
    chunks, dataset, freeze, corpus_hash = read_fixture()
    if (source["dataset_version"] != dataset["dataset_version"] or source["freeze"] != freeze or
            source["index_manifest"]["corpus_sha256"] != corpus_hash or
            source["reserved_cases_evaluated"] is not False):
        raise ValueError("基线与冻结开发材料不一致，不能直接做前后对照")
    known = {chunk["id"]: chunk for chunk in chunks}
    questions = {case["id"]: case for case in dataset["cases"]}
    for case in source["cases"]:
        gold = questions[case["id"]]
        if any(case[key] != gold[key] for key in ("question", "required_ids")):
            raise ValueError("报告中的问题或标注与冻结题目不一致")
        candidates = case["methods"]["rrf"]["candidates"]
        if len({hit["chunk"]["id"] for hit in candidates}) != len(candidates):
            raise ValueError("RRF 候选不应有重复 ID")
        if any(known[hit["chunk"]["id"]] != hit["chunk"] for hit in candidates):
            raise ValueError("候选正文与冻结语料不一致")
        if candidates[:source["top_k"]] != case["methods"]["rrf"]["hits"]:
            raise ValueError("基线最终结果与候选顺序不一致")
    return source, hashlib.sha256(raw).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="同一问题、同一 RRF 候选、同一最终 K 的重排比较")
    parser.add_argument("--source-report", type=Path, default=BASELINE)
    parser.add_argument("--case", default="paraphrase_receipts")
    parser.add_argument("--all", action="store_true", help="重排全部 30 条公开开发题")
    args = parser.parse_args(argv)
    source, source_hash = load_baseline(args.source_report)
    cases = source["cases"] if args.all else [case for case in source["cases"] if case["id"] == args.case]
    if not cases:
        parser.error("基线没有这个案例")
    print(f"重放 {len(cases)} 题的原 RRF 候选；最终 K={source['top_k']}；不重新编码或召回。", flush=True)
    started = time.perf_counter()
    load_reranker()
    load_ms = round((time.perf_counter() - started) * 1000)
    records = []
    for case in cases:
        candidates = copy.deepcopy(case["methods"]["rrf"]["candidates"])
        trace = {}

        def tracked_scores(pairs):
            tick = time.perf_counter()
            values = score_pairs(pairs)
            trace["inference_ms"] = round((time.perf_counter() - tick) * 1000)
            trace["scores"] = values
            return values

        after = rerank_candidates(case["question"], candidates, tracked_scores, top_k=source["top_k"])
        # 按学生函数的相同稳定规则保存全候选新排名，便于观察第三名之后的变化。
        all_scored = sorted([
            {"chunk": hit["chunk"], "score": float(score), "retrieval_score": float(hit["score"])}
            for hit, score in zip(candidates, trace["scores"])
        ], key=lambda hit: hit["score"], reverse=True)
        if after != all_scored[:source["top_k"]]:
            raise ValueError("函数输出与实际模型评分的关联或排序不一致")
        before_metrics = case["methods"]["rrf"]
        after_metrics = measurement(candidates, after, case["required_ids"])
        delta = after_metrics["evidence_recall"] - before_metrics["evidence_recall"]
        outcome = "improved" if delta > 0 else "regressed" if delta < 0 else "unchanged"
        records.append({
            "id": case["id"], "question": case["question"], "category": case["category"],
            "required_ids": case["required_ids"], "candidates": candidates,
            "before": before_metrics, "after": after_metrics,
            "all_reranked": all_scored, "outcome": outcome, "inference_ms": trace["inference_ms"],
        })
        print(f"\n{case['id']}：{case['question']}", flush=True)
        print(f"重排前：{[hit['chunk']['heading'] for hit in before_metrics['hits']]} | 召回={before_metrics['evidence_recall']:.0%}")
        print(f"重排后：{[hit['chunk']['heading'] for hit in after]} | 召回={after_metrics['evidence_recall']:.0%} | {outcome} | {trace['inference_ms']} ms")
        if len(cases) == 1:
            for rank, hit in enumerate(all_scored, 1):
                print(f"  {rank}. {hit['chunk']['heading']} | logit={hit['score']:.4f} | {hit['chunk']['id']}")
    summary = {
        stage: {
            "mean_evidence_recall": sum(row[stage]["evidence_recall"] for row in records) / len(records),
            "all_required_found_rate": sum(row[stage]["all_required_found"] for row in records) / len(records),
        }
        for stage in ("before", "after")
    }
    changes = {name: [row["id"] for row in records if row["outcome"] == name]
               for name in ("improved", "regressed", "unchanged")}
    now = datetime.now(timezone(timedelta(hours=8)))
    record = {
        "run_time": now.isoformat(), "source_report": str(args.source_report.resolve()),
        "source_report_sha256": source_hash, "dataset_version": source["dataset_version"],
        "case_count": len(cases), "candidate_k": source["candidate_k"], "top_k": source["top_k"],
        "reranker": reranker_metadata(), "model_load_ms": load_ms,
        "packages": {name: version(name) for name in ("sentence-transformers", "transformers", "torch", "numpy")},
        "summary": summary, "changes": changes, "cases": records,
        "reserved_cases_evaluated": False,
        "note": "公开开发题、固定原始 RRF 候选；只改变排序。CPU 单次推理计时，不是并发基准；未调用聊天 API，未重建索引，未评价生成和拒答。模型 logit 不作为正确率。",
    }
    path = ROOT / "reports" / f"reranker-eval-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"改善 {len(changes['improved'])} 题，退步 {len(changes['regressed'])} 题，不变 {len(changes['unchanged'])} 题。")
    print(f"报告：{path}")
    print("仅本地重排；未调用聊天模型，预留题未评估。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
