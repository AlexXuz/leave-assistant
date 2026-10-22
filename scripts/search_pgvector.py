"""数据库检索与文件基线对照；不调用聊天模型。"""

import argparse

import numpy as np
from pgvector.psycopg import register_vector

from app.embeddings import embed_query
from app.pgvector_retrieval import search_pgvector
from app.pgvector_store import check_collection, connect_database
from app.retrieval import rank_chunks
from app.vector_index import load_index


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="休四天年假要找谁批准？")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--compare", action="store_true", help="比较同一快照的 NumPy 与数据库结果")
    args = parser.parse_args(argv)
    if args.top_k < 1:
        parser.error("K 必须至少为 1")
    query = embed_query(args.question)
    with connect_database() as connection:
        register_vector(connection)
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            manifest = check_collection(connection)
            hits = search_pgvector(connection, query, args.top_k)
    for index, hit in enumerate(hits, 1):
        print(f"{index}. {hit['chunk']['id']} | {hit['chunk']['heading']} | {hit['score']:.6f}")
    if args.compare:
        chunks, vectors, baseline_manifest = load_index()
        if baseline_manifest != manifest:
            raise ValueError("文件与数据库不是同一批索引快照，不能直接对照")
        expected = rank_chunks(query, vectors, chunks, args.top_k)
        if [row["chunk"] for row in hits] != [row["chunk"] for row in expected]:
            raise AssertionError("片段内容或排序不同；检查数据、距离函数及同分规则")
        if not np.allclose([row["score"] for row in hits], [row["score"] for row in expected], atol=1e-6, rtol=0):
            raise AssertionError("分数与 NumPy 基线不一致；检查距离是否转换为相似度")
        print("PASS: 同一问题向量、同一文档向量，片段与排序一致，分数误差在 1e-6 内。")
    print("本次仅本地 Embedding 与数据库检索，未调用聊天模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
