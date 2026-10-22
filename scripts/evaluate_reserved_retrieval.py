"""Day 6 收尾：固定配置评估十条预留题；完成后重复运行只展示已有报告。"""

import argparse
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from importlib.metadata import version

from app.embeddings import embed_query
from app.hybrid_retrieval import fuse_rrf
from app.keyword_retrieval import KeywordIndex
from app.local_reranker import load_reranker, reranker_metadata, score_pairs
from app.reranking import rerank_candidates
from app.retrieval import rank_chunks
from scripts.retrieval_lab import LAB, ROOT, load_index, measurement, read_fixture

CONFIG_PATH = LAB / "rerank_candidate_v1.json"
RESULT_POINTER = LAB / "reserved_result_v1.json"


def read_fixed_experiment():
    config_bytes = CONFIG_PATH.read_bytes()
    config = json.loads(config_bytes)
    chunks, _, freeze, corpus_hash = read_fixture()
    vectors, manifest = load_index(chunks, corpus_hash)
    dev_bytes = (ROOT / config["development_report"]).read_bytes()
    dev = json.loads(dev_bytes)
    if (hashlib.sha256(dev_bytes).hexdigest() != config["development_report_sha256"] or
            config["freeze"] != freeze or config["corpus_sha256"] != corpus_hash or
            config["embedding"] != manifest["embedding"] or
            config["reranker"] != reranker_metadata() or config["reranker"] != dev["reranker"]):
        raise ValueError("模型、材料或开发报告与锁定配置不一致，不运行预留题")
    if (config["candidate_strategy"] != "equal-weight-rrf" or
            config["candidate_k"] != dev["candidate_k"] or config["top_k"] != dev["top_k"] or
            config["rank_constant"] != freeze["initial_config"]["rank_constant"] or
            config["keyword_config"] != {"HMM": False, "mode": "search", "k1": 1.5, "b": 0.75, "epsilon": 0.25}):
        raise ValueError("检索策略与已锁定实现不一致")
    packages = {name: version(name) for name in dev["packages"]}
    if packages != dev["packages"]:
        raise ValueError("运行库版本与开发实验不一致，请记录为新实验")
    dataset = json.loads((LAB / "reserved_cases.json").read_text(encoding="utf-8"))
    return chunks, vectors, manifest, dataset, config, hashlib.sha256(config_bytes).hexdigest(), packages


def collect_candidates(cases, chunks, vectors, config):
    keyword = KeywordIndex(chunks)
    prepared = []
    for case in cases:
        # 人工答案和必要证据不参与编码、词项检索或排名融合。
        vector_hits = rank_chunks(embed_query(case["question"]), vectors, chunks, config["candidate_k"])
        bm25_hits = keyword.search(case["question"], config["candidate_k"])
        rrf_hits = fuse_rrf([vector_hits, bm25_hits], config["candidate_k"], config["rank_constant"])
        prepared.append((case, {"vector": vector_hits, "bm25": bm25_hits, "rrf": rrf_hits}))
        print(f"候选已固定：{case['id']}", flush=True)
    return prepared


def evaluate_prepared(prepared, config, scorer=None):
    if scorer is None:
        scorer = score_pairs
    rows = []
    for case, candidates in prepared:
        trace = {}

        def tracked(pairs):
            started = time.perf_counter()
            values = scorer(pairs)
            trace.update(scores=values, inference_ms=round((time.perf_counter() - started) * 1000))
            return values

        selected = rerank_candidates(case["question"], candidates["rrf"], tracked, config["top_k"])
        all_reranked = sorted([
            {"chunk": hit["chunk"], "score": float(score), "retrieval_score": float(hit["score"])}
            for hit, score in zip(candidates["rrf"], trace["scores"])
        ], key=lambda hit: hit["score"], reverse=True)
        if selected != all_reranked[:config["top_k"]]:
            raise ValueError("重排结果与模型评分关联不一致")
        methods = {
            name: measurement(hits, hits[:config["top_k"]], case["required_ids"])
            for name, hits in candidates.items()
        }
        methods["reranked"] = measurement(candidates["rrf"], selected, case["required_ids"])
        delta = methods["reranked"]["evidence_recall"] - methods["rrf"]["evidence_recall"]
        outcome = "improved" if delta > 0 else "regressed" if delta < 0 else "unchanged"
        rows.append({**case, "methods": methods, "all_reranked": all_reranked,
                     "outcome": outcome, "inference_ms": trace["inference_ms"]})
        print(f"{case['id']}: RRF={methods['rrf']['evidence_recall']:.0%} → 重排={methods['reranked']['evidence_recall']:.0%} | {outcome}", flush=True)
    return rows


def summarize(rows):
    count = len(rows)
    return {
        name: {
            "mean_evidence_recall": sum(row["methods"][name]["evidence_recall"] for row in rows) / count,
            "all_required_found_count": sum(row["methods"][name]["all_required_found"] for row in rows),
            "all_required_found_rate": sum(row["methods"][name]["all_required_found"] for row in rows) / count,
            "candidate_all_required_found_count": sum(row["methods"][name]["candidate_all_required_found"] for row in rows),
        }
        for name in ("vector", "bm25", "rrf", "reranked")
    }


def show_report(record, path):
    print("\n策略 | 平均必要证据召回 | 找齐全部必要证据")
    for name, value in record["summary"].items():
        print(f"{name} | {value['mean_evidence_recall']:.1%} | {value['all_required_found_count']}/{record['case_count']}")
    print("重排相对 RRF：" + "; ".join(f"{name}={len(ids)}" for name, ids in record["changes"].items()))
    print(f"报告：{path}")
    print("这是固定配置下的同领域预留题检索结果，不是回答准确率；不据此继续调参。")


def main(argv=None):
    parser = argparse.ArgumentParser(description="只用锁定配置运行预留题；再次执行时展示已有结果")
    parser.add_argument("--verify-only", action="store_true", help="只检查配置，不运行任何预留题推理")
    args = parser.parse_args(argv)
    chunks, vectors, manifest, dataset, config, config_hash, packages = read_fixed_experiment()
    if args.verify_only:
        print(f"配置校验通过：{config['config_id']}；{len(dataset['cases'])} 道预留题尚未在本次执行中推理。")
        return 0
    if RESULT_POINTER.exists():
        pointer = json.loads(RESULT_POINTER.read_text(encoding="utf-8"))
        if pointer["config_sha256"] != config_hash:
            raise ValueError("预留题已有结果且配置发生变化，不重复选参")
        path = ROOT / pointer["report"]
        print("已有完整预留题报告，直接展示；不重复运行模型。")
        show_report(json.loads(path.read_text(encoding="utf-8")), path)
        return 0
    print(f"固定配置 {config['config_id']}，{len(dataset['cases'])} 题，候选 {config['candidate_k']}、最终 {config['top_k']}。", flush=True)
    prepared = collect_candidates(dataset["cases"], chunks, vectors, config)
    started = time.perf_counter()
    load_reranker()
    load_ms = round((time.perf_counter() - started) * 1000)
    rows = evaluate_prepared(prepared, config)
    now = datetime.now(timezone(timedelta(hours=8)))
    record = {
        "run_time": now.isoformat(), "config_sha256": config_hash, "config": config,
        "dataset_version": dataset["dataset_version"], "case_count": len(rows),
        "index_manifest": manifest, "packages": packages, "model_load_ms": load_ms,
        "summary": summarize(rows),
        "changes": {name: [row["id"] for row in rows if row["outcome"] == name]
                    for name in ("improved", "regressed", "unchanged")},
        "cases": rows, "reserved_cases_evaluated": True,
        "note": "配置先锁定，预留题只做本次同领域核对；与开发题共享制度事实及部分业务家族，不声称外部独立泛化。仅比较必要证据，未调用聊天模型或评价生成质量。",
    }
    path = ROOT / "reports" / f"reserved-retrieval-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    with RESULT_POINTER.open("x", encoding="utf-8") as handle:
        json.dump({"config_sha256": config_hash, "report": str(path.relative_to(ROOT))}, handle, ensure_ascii=False, indent=2)
    show_report(record, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
