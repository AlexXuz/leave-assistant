"""本地向量检索；--demo 查看向量与未排序分数，不调用聊天 API。"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.embeddings import embed_documents, embed_query, embedding_metadata
from app.course.examples.foundations.retrieval import rank_chunks

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="本地 Embedding 与向量检索")
    parser.add_argument("--question", default="休四天年假要找谁批准？")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--demo", action="store_true", help="只展示向量信息和原始分数，不调用待实现的排序函数")
    args = parser.parse_args(argv)
    if args.top_k < 1:
        parser.error("--top-k 必须至少为 1")
    path = PROJECT_ROOT / "data/policy_chunks.json"
    if not path.exists():
        parser.error("请先运行 python -m scripts.check_policy_chunks --write")
    chunks = json.loads(path.read_text(encoding="utf-8"))
    if not chunks:
        parser.error("片段文件不能为空")
    print(f"开始本地编码：{len(chunks)} 个片段，CPU；不调用 DeepSeek。", flush=True)
    chunk_vectors = embed_documents([chunk["content"] for chunk in chunks])
    query_vector = embed_query(args.question)
    print(f"片段向量 shape={chunk_vectors.shape}；问题向量 shape={query_vector.shape}")
    print(f"问题向量前 8 个数：{query_vector[:8].tolist()}")
    # 向量均已归一化，点积等于余弦相似度。
    scores = chunk_vectors @ query_vector
    if args.demo:
        for chunk, score in zip(chunks, scores):
            print(f"{float(score):.4f}  {chunk['id']}  {chunk['heading']}")
        print("以上按原文顺序展示，尚未排序；分数不是答案正确概率。")
        return 0
    try:
        results = rank_chunks(query_vector, chunk_vectors, chunks, args.top_k)
    except NotImplementedError as error:
        print(error)
        return 2
    now = datetime.now(timezone(timedelta(hours=8)))
    report = {
        "run_time": now.isoformat(), "question": args.question,
        "top_k": args.top_k, "embedding": embedding_metadata(),
        "chunk_ids_in_vector_order": [chunk["id"] for chunk in chunks],
        "results": results,
        "note": "只报告检索候选，不代表已有足够回答证据；本轮未调用聊天模型。",
    }
    directory = PROJECT_ROOT / "reports"
    directory.mkdir(exist_ok=True)
    report_path = directory / f"retrieval-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for rank, result in enumerate(results, start=1):
        chunk = result["chunk"]
        print(f"\n第 {rank} 名，score={result['score']:.4f}，{chunk['id']}")
        print(chunk["content"])
    print(f"\n报告：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
