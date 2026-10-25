"""RAG 运行器：默认只预览；--run 才调用一次聊天模型。"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.embeddings import embedding_metadata
from app.course.examples.foundations.exercises import call_model
from app.course.examples.foundations.policy_qa import parse_policy_answer
from app.course.examples.foundations.rag_qa import RAG_PROMPT_VERSION, prepare_rag_request

REPORTS_DIRECTORY = Path(__file__).resolve().parents[1] / "reports"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="最小 RAG：默认预览，不调用聊天模型")
    parser.add_argument("--question", default="休四天年假要找谁批准？")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--run", action="store_true", help="调用一次真实聊天模型并保存报告")
    args = parser.parse_args(argv)
    if args.top_k < 1:
        parser.error("--top-k 必须至少为 1")
    try:
        prepared = prepare_rag_request(args.question, args.top_k)
    except NotImplementedError as error:
        print(f"待完成：{error}；未调用聊天模型")
        return 2
    if not isinstance(prepared, dict) or set(prepared) != {"retrieved_chunks", "documents", "messages"}:
        raise ValueError("prepare_rag_request 必须返回约定的三个键")
    hits = prepared["retrieved_chunks"]
    documents = prepared["documents"]
    expected_documents = [
        {"id": hit["chunk"]["id"], "content": hit["chunk"]["content"]}
        for hit in hits
    ]
    if documents != expected_documents:
        raise ValueError("参考资料应只包含实际命中片段的 ID 和正文，顺序与命中结果一致")
    print("检索后端：PostgreSQL + pgvector")
    for index, hit in enumerate(hits, start=1):
        print(f"检索第 {index} 名：{hit['chunk']['id']}，score={hit['score']:.4f}")
    if not args.run:
        print(json.dumps(prepared["messages"], ensure_ascii=False, indent=2))
        print("预览完成；已运行本地检索，未调用聊天模型。请检查证据是否覆盖问题。")
        return 0

    now = datetime.now(timezone(timedelta(hours=8)))
    record = {
        "run_time": now.isoformat(), "question": args.question, "top_k": args.top_k,
        "prompt_version": RAG_PROMPT_VERSION, "embedding": embedding_metadata(),
        "retrieval_backend": "pgvector",
        **prepared, "raw_content": None, "actual": None,
        "manual_review_required": True,
        "note": "结构有效和来源存在不代表检索证据充分或回答正确，仍需人工复核。",
    }
    stage = "call"
    try:
        record["raw_content"] = call_model(prepared["messages"], prompt_version=RAG_PROMPT_VERSION)
        stage = "parse"
        record["actual"] = parse_policy_answer(record["raw_content"], documents)
        record["structure_valid"] = True
    except Exception as error:
        record.update(structure_valid=False, error_stage=stage, error_type=type(error).__name__)
    record["configured_model"] = os.getenv("LLM_MODEL")
    REPORTS_DIRECTORY.mkdir(exist_ok=True)
    report_path = REPORTS_DIRECTORY / f"rag-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    report_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record["actual"], ensure_ascii=False, indent=2))
    if "error_type" in record:
        print(f"失败阶段：{record['error_stage']}；异常类型：{record['error_type']}")
    print(f"报告：{report_path}")
    return 0 if record["structure_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
