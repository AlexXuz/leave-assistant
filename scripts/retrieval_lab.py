"""助教提供：独立语料实验，复用本地 Embedding 和已验收的检索函数。"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from app.embeddings import embed_documents, embed_query, embedding_metadata
from app.course.examples.foundations.hybrid_retrieval import fuse_rrf
from app.keyword_retrieval import KeywordIndex
from app.course.examples.foundations.retrieval import rank_chunks, split_policy_document
from app.course.examples.foundations.retrieval_metrics import evaluate_evidence

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "retrieval_lab_v2"
INDEX = ROOT / "data" / "indexes" / "retrieval-lab-v2.npz"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_fixture():
    freeze = json.loads((LAB / "freeze.json").read_text(encoding="utf-8"))
    raw = {}
    for name, expected in freeze["files_sha256"].items():
        content = (LAB / name).read_bytes()
        if digest(content) != expected:
            raise ValueError(f"实验材料已变化：{name}；需要新版本，不能沿用原冻结记录")
        raw[name] = json.loads(content)
    chunks = raw["base_chunks.json"]
    for document in raw["additional_policies.json"]["documents"]:
        content = "\n\n".join(f"## {section['heading']}\n{section['body']}" for section in document["sections"])
        chunks.extend(split_policy_document({
            "id": document["id"], "title": document["title"],
            "version": raw["additional_policies.json"]["version"], "content": content,
        }))
    ids = {chunk["id"] for chunk in chunks}
    if len(ids) != len(chunks):
        raise ValueError("片段 ID 重复")
    for name in ("dev_cases.json", "reserved_cases.json"):
        cases = raw[name]["cases"]
        if len({case["id"] for case in cases}) != len(cases):
            raise ValueError("案例 ID 重复")
        for case in cases:
            if not case["question"].strip() or not case["answer_points"]:
                raise ValueError("题目和答案要点不能空")
            if not case["required_ids"] or not set(case["required_ids"]) <= ids:
                raise ValueError(f"标注证据不存在：{case['id']}")
    serialized = json.dumps(chunks, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return chunks, raw["dev_cases.json"], freeze, digest(serialized)


def build_index(chunks, corpus_hash, freeze):
    if INDEX.exists():
        load_index(chunks, corpus_hash)
        print(f"已有独立实验索引通过校验，无需重复编码：{INDEX}")
        return
    vectors = np.asarray(embed_documents([chunk["content"] for chunk in chunks]), dtype=np.float32)
    manifest = {
        "corpus_sha256": corpus_hash, "embedding": embedding_metadata(),
        "vectors_sha256": digest(vectors.tobytes()), "freeze": freeze,
        "chunk_count": len(chunks), "dimension": vectors.shape[1],
    }
    INDEX.parent.mkdir(exist_ok=True)
    with INDEX.open("xb") as handle:
        np.savez_compressed(handle, vectors=vectors,
                            manifest=np.array(json.dumps(manifest, ensure_ascii=False)))
    print(f"已编码 {len(chunks)} 条独立实验片段：{INDEX}")


def load_index(chunks, corpus_hash):
    if not INDEX.exists():
        raise FileNotFoundError("请先运行 scripts.retrieval_lab --build，构建独立实验索引")
    with np.load(INDEX, allow_pickle=False) as archive:
        vectors = archive["vectors"].copy()
        manifest = json.loads(archive["manifest"].item())
    if manifest["corpus_sha256"] != corpus_hash or manifest["embedding"] != embedding_metadata():
        raise ValueError("独立实验索引和当前语料或 Embedding 配置不一致")
    if vectors.shape != (len(chunks), manifest["dimension"]) or not np.isfinite(vectors).all():
        raise ValueError("向量形状或数值无效")
    if digest(vectors.tobytes()) != manifest["vectors_sha256"]:
        raise ValueError("实验向量校验失败")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5):
        raise ValueError("实验向量必须归一化")
    return vectors, manifest


def measurement(candidates, selected, required):
    candidate_metrics = evaluate_evidence([row["chunk"]["id"] for row in candidates], required)
    final_metrics = evaluate_evidence([row["chunk"]["id"] for row in selected], required)
    candidate_missing = not candidate_metrics["all_required_found"]
    ranking_loss = bool(set(required).intersection(row["chunk"]["id"] for row in candidates)
                        - set(row["chunk"]["id"] for row in selected))
    return {
        **final_metrics,
        "candidate_evidence_recall": candidate_metrics["evidence_recall"],
        "candidate_all_required_found": candidate_metrics["all_required_found"],
        "candidate_missing_ids": candidate_metrics["missing_ids"],
        "candidate_missing": candidate_missing, "ranking_loss": ranking_loss,
        "diagnosis": "candidate_missing" if candidate_missing else
                     "ranking_loss" if ranking_loss else "covered",
        "candidates": candidates, "hits": selected,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="固定的独立检索实验；不调用聊天模型或数据库")
    parser.add_argument("--build", action="store_true", help="只编码独立实验文档并保存索引")
    parser.add_argument("--case", help="仅运行指定公开调试案例")
    parser.add_argument("--candidate-k", type=int, default=6)
    parser.add_argument("--top-k", type=int, default=2)
    args = parser.parse_args(argv)
    if not 1 <= args.top_k <= args.candidate_k:
        parser.error("要求 1 <= top-k <= candidate-k")
    chunks, dataset, freeze, corpus_hash = read_fixture()
    if args.build:
        build_index(chunks, corpus_hash, freeze)
        return 0
    vectors, manifest = load_index(chunks, corpus_hash)
    cases = [case for case in dataset["cases"] if case["id"] == args.case] if args.case else dataset["cases"]
    if not cases:
        parser.error("没有这个公开调试案例")
    keyword = KeywordIndex(chunks)
    records = []
    print(f"{len(chunks)} 片段，{len(cases)} 道公开题；每路及 RRF 候选池最多 {args.candidate_k} 条，最终 {args.top_k} 条。", flush=True)
    for case in cases:
        # 只有 question 进入检索；必要证据和答案要点只在检索完成后用于评测。
        vector_hits = rank_chunks(embed_query(case["question"]), vectors, chunks, args.candidate_k)
        keyword_hits = keyword.search(case["question"], args.candidate_k)
        pooled = fuse_rrf([vector_hits, keyword_hits], top_k=args.candidate_k, rank_constant=60)
        methods = {
            name: measurement(candidates, candidates[:args.top_k], case["required_ids"])
            for name, candidates in (("vector", vector_hits), ("bm25", keyword_hits), ("rrf", pooled))
        }
        records.append({**case, "methods": methods})
        brief = " | ".join(f"{name}: {value['evidence_recall']:.0%}/{value['diagnosis']}" for name, value in methods.items())
        print(f"{case['id']}: {brief}", flush=True)
    summary = {}
    for name in ("vector", "bm25", "rrf"):
        values = [row["methods"][name] for row in records]
        summary[name] = {
            "mean_evidence_recall": sum(v["evidence_recall"] for v in values) / len(values),
            "all_required_found_rate": sum(v["all_required_found"] for v in values) / len(values),
            "candidate_all_required_found_rate": sum(v["candidate_all_required_found"] for v in values) / len(values),
            "diagnosis_counts": dict(Counter(v["diagnosis"] for v in values)),
        }
    now = datetime.now(timezone(timedelta(hours=8)))
    record = {
        "run_time": now.isoformat(), "dataset_version": dataset["dataset_version"],
        "case_count": len(cases), "chunk_count": len(chunks), "freeze": freeze,
        "index_manifest": manifest, "candidate_k": args.candidate_k, "top_k": args.top_k,
        "rank_constant": 60, "retrieval_backend": "isolated-numpy+bm25",
        "keyword_config": {"HMM": False, "mode": "search", "k1": 1.5, "b": 0.75, "epsilon": 0.25},
        "reserved_cases_evaluated": False, "summary": summary, "cases": records,
        "note": "模拟小语料的公开开发题；固定材料后首次运行，不作为生产准确率。先独立观察策略；尚未启用真实 Reranker。预留题未运行。",
    }
    directory = ROOT / "reports"
    directory.mkdir(exist_ok=True)
    path = directory / f"retrieval-lab-v2-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"报告：{path}")
    print("未请求聊天模型；未连接或改动现有数据库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
