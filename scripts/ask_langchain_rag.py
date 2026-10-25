"""助教运行器：默认只预览 LangChain 准备链，--run 才调用一次聊天模型。"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

from langsmith import tracing_context

from app.langchain_model import generate_step
from app.course.examples.foundations.langchain_rag import build_prepare_chain, validate_step
from app.course.examples.foundations.policy_qa import build_policy_messages
from app.course.examples.foundations.rag_qa import RAG_PROMPT_VERSION

REPORTS_DIRECTORY = Path(__file__).resolve().parents[1] / "reports"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LangChain RAG：默认预览")
    parser.add_argument("--question", default="休四天年假要找谁批准？")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if args.top_k < 1:
        parser.error("--top-k 必须至少为 1")
    # 本课只保存本地报告；不启用外部 LangSmith 跟踪。
    with tracing_context(enabled=False):
        return run(args)


def run(args) -> int:
    try:
        state = build_prepare_chain().invoke({"question": args.question, "top_k": args.top_k})
    except NotImplementedError as error:
        print(f"待完成：{error}；未调用聊天模型")
        return 2
    except Exception as error:
        print(f"准备阶段失败：{type(error).__name__}；未调用聊天模型")
        return 1
    expected_documents = [
        {"id": hit["chunk"]["id"], "content": hit["chunk"]["content"]}
        for hit in state["retrieved_chunks"]
    ]
    if (state["documents"] != expected_documents or
            state["messages"] != build_policy_messages(args.question, expected_documents)):
        raise ValueError("转换改变了片段、顺序或消息；请先修复，不调用模型")
    print("检索后端：PostgreSQL + pgvector；编排：LangChain")
    for index, document in enumerate(state["lc_documents"], start=1):
        print(f"第 {index} 名：{document.id}，metadata={document.metadata}")
    print("同一批命中的片段 ID、正文及最终消息与原生构造方式完全一致。")
    if not args.run:
        print(json.dumps(state["messages"], ensure_ascii=False, indent=2))
        print("预览完成；已运行本地检索，未调用聊天模型。")
        return 0
    now = datetime.now(timezone(timedelta(hours=8)))
    record = {
        **state,
        "lc_documents": [document.model_dump(mode="json") for document in state["lc_documents"]],
        "run_time": now.isoformat(),
        "framework": {name: version(name) for name in ("langchain-core", "langchain-deepseek")},
        "retrieval_backend": "pgvector", "prompt_version": RAG_PROMPT_VERSION,
        "raw_content": None, "actual": None, "manual_review_required": True,
        "note": "结构及引用存在检查通过，不代表答案语义和引用支持性通过。",
    }
    stage = "call"
    try:
        generated = generate_step(state)
        record.update(raw_content=generated["raw_content"], model_metadata=generated["model_metadata"])
        stage = "parse"
        record["actual"] = validate_step(generated)["actual"]
        record["structure_valid"] = True
    except Exception as error:
        record.update(structure_valid=False, error_stage=stage, error_type=type(error).__name__)
    REPORTS_DIRECTORY.mkdir(exist_ok=True)
    path = REPORTS_DIRECTORY / f"langchain-rag-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record["actual"], ensure_ascii=False, indent=2))
    if "error_type" in record:
        print(f"失败阶段：{record['error_stage']}；异常类型：{record['error_type']}")
    print(f"报告：{path}")
    return 0 if record["structure_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
