"""助教实验：同一数据库快照，比较向量、BM25 与 RRF；不生成回答。"""

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

from pgvector.psycopg import register_vector

from app.embeddings import embed_query
from app.hybrid_retrieval import fuse_rrf
from app.keyword_retrieval import KeywordIndex
from app.pgvector_retrieval import search_pgvector
from app.pgvector_store import CHUNK_FIELDS, COLLECTION_NAME, check_collection, connect_database
from app.retrieval_metrics import evaluate_evidence

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def collect_rankings(cases, candidate_k):
    # 模型加载及问题编码发生在打开数据库连接之前，每题只编码一次。
    queries = [embed_query(case["question"]) for case in cases]
    with connect_database() as connection:
        register_vector(connection)
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            manifest = check_collection(connection)
            rows = connection.execute(
                "SELECT id, document_id, title, version, heading, content "
                "FROM leave_assistant_lab.policy_chunks WHERE collection = %s ORDER BY position",
                (COLLECTION_NAME,),
            ).fetchall()
            chunks = [{key: row[key] for key in CHUNK_FIELDS} for row in rows]
            vectors = [search_pgvector(connection, query, candidate_k) for query in queries]
    keyword = KeywordIndex(chunks)
    rankings = [
        {"vector": hits, "bm25": keyword.search(case["question"], candidate_k),
         "query_tokens": keyword.tokenize(case["question"])}
        for case, hits in zip(cases, vectors)
    ]
    return rankings, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="同一语料、同一最终 K 的检索策略比较")
    parser.add_argument("--case", default="leave_and_remote")
    parser.add_argument("--all", action="store_true", help="比较已有 12 条公开调试题")
    parser.add_argument("--candidate-k", type=int, default=4)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--rank-constant", type=int, default=60)
    parser.add_argument("--baseline-only", action="store_true", help="作业前只看向量和 BM25")
    args = parser.parse_args(argv)
    if not 1 <= args.top_k <= args.candidate_k or args.rank_constant < 1:
        parser.error("要求 1 <= top-k <= candidate-k，rank-constant >= 1")
    if not args.baseline_only:
        try:
            fuse_rrf([], args.top_k, args.rank_constant)
        except NotImplementedError as error:
            print(f"待完成：{error}；先运行 scripts.check_rrf，未加载模型、未连接数据库")
            return 2
    dataset_bytes = (PROJECT_ROOT / "data" / "retrieval_cases.json").read_bytes()
    dataset = json.loads(dataset_bytes)
    cases = dataset["cases"] if args.all else [case for case in dataset["cases"] if case["id"] == args.case]
    if not cases:
        parser.error("没有找到这个 case ID")
    print(f"{len(cases)} 题；每路候选最多 {args.candidate_k} 条，最终各取 {args.top_k} 条。", flush=True)
    rankings, manifest = collect_rankings(cases, args.candidate_k)
    known_ids = set(manifest["ordered_chunk_ids"])
    if any(not set(case["required_ids"]) <= known_ids for case in cases):
        raise ValueError("标注证据不在当前集合中")
    records = []
    for case, routes in zip(cases, rankings):
        selected = {name: routes[name][:args.top_k] for name in ("vector", "bm25")}
        if not args.baseline_only:
            selected["rrf"] = fuse_rrf([routes["vector"], routes["bm25"]], args.top_k, args.rank_constant)
        measurements = {}
        print(f"\n{case['id']}：{case['question']}")
        print(f"分词：{routes['query_tokens']}")
        for name, hits in selected.items():
            ids = [hit["chunk"]["id"] for hit in hits]
            metrics = evaluate_evidence(ids, case["required_ids"])
            measurements[name] = {
                **metrics, "hits": hits,
                "context_chars": sum(len(hit["chunk"]["content"]) for hit in hits),
            }
            print(f"{name}: {[hit['chunk']['heading'] for hit in hits]} | 证据召回={metrics['evidence_recall']:.0%} | 缺失={metrics['missing_ids']}")
        records.append({**case, "routes": routes, "methods": measurements})
    methods = list(records[0]["methods"])
    summary = {
        name: {
            "mean_evidence_recall": sum(row["methods"][name]["evidence_recall"] for row in records) / len(records),
            "all_required_found_rate": sum(row["methods"][name]["all_required_found"] for row in records) / len(records),
        }
        for name in methods
    }
    print("\n汇总：" + json.dumps(summary, ensure_ascii=False))
    now = datetime.now(timezone(timedelta(hours=8)))
    record = {
        "run_time": now.isoformat(), "dataset_version": dataset["dataset_version"],
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(), "index_manifest": manifest,
        "case_count": len(cases), "candidate_k": args.candidate_k, "top_k": args.top_k,
        "rank_constant": args.rank_constant, "retrieval_backend": "pgvector+in-memory-bm25",
        "keyword_config": {"tokenizer": "jieba.lcut_for_search", "HMM": False,
                           "filter": "casefold+isalnum", "k1": 1.5, "b": 0.75, "epsilon": 0.25},
        "packages": {name: version(name) for name in ("jieba", "rank-bm25")},
        "summary": summary, "cases": records,
        "note": "公开的七片段小语料调试实验，非保留集；只评必要证据召回，不评回答质量或生产性能。BM25 从同一数据库快照全量读取正文，在内存中建立教学索引。未调用聊天模型，未修改数据库或现有问答入口。",
    }
    directory = PROJECT_ROOT / "reports"
    directory.mkdir(exist_ok=True)
    path = directory / f"hybrid-eval-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告：{path}")
    print("仅本地 Embedding 与只读数据库检索，未调用聊天模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
