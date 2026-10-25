"""Day 9 Word 问答：真实本地向量、数据库和章节引用；--run 才调用 DeepSeek。"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import time
from uuid import uuid4

from pgvector.psycopg import register_vector

from app.course.examples.foundations.docx_chunking import build_docx_chunks
from app.docx_preparation import prepare_sample_docx
from app.document_manifest import build_document_manifest
from app.course.examples.foundations.document_sync import plan_document_sync
from app.course.examples.foundations.document_sync_execution import apply_sync_batch
from app.embeddings import embed_documents, load_embedding_model
from app.course.examples.foundations.pdf_ingestion import DocumentParseError
from app.course.examples.foundations.permission_rag import prepare_authorized_rag_request
from app.permission_service import TrustedAccessContext
from app.pgvector_store import PROJECT_ROOT, connect_database
from app.course.examples.foundations.policy_qa import parse_policy_answer
from app.course.examples.foundations.source_citations import resolve_citations
from app.vector_index import current_embedding_config
from scripts.ask_pdf_rag import tracked_model_call

PROMPT_VERSION = "docx-policy-rag-v1"
CASES = {
    "city_limits": {"question": "北京和上海与其他城市的住宿报销上限分别是多少？金额按什么单位计算？",
                    "expected_can_answer": True, "required_sections": ["住宿标准"],
                    "manual_check": "核对两类城市的数值及每人每晚单位，避免混淆行列。"},
    "combined": {"question": "去上海出差住酒店，每人每晚最多报销多少？如果超标要提前取得什么批准？报销住宿还需要哪些凭证？",
                 "expected_can_answer": True, "required_sections": ["住宿标准", "申请与凭证"],
                 "manual_check": "金额、预订前/部门经理/书面批准、住宿发票及订单记录均需完整，引用覆盖两章。"},
    "unknown": {"question": "出差每天的餐费补贴是多少元？",
                "expected_can_answer": False, "required_sections": [],
                "manual_check": "文档未规定标准，应说明资料不足，不编造金额。"},
}


def prepare_word(profile_path=None):
    sample = prepare_sample_docx(profile_path)
    chunks = build_docx_chunks(sample["document"], sample["blocks"])
    document = {**sample["document"], "content": "\n\n".join(chunk["content"] for chunk in chunks),
                "visibility": "department", "allowed_departments": ["engineering"]}
    config = current_embedding_config()
    manifest = build_document_manifest(document, config, chunks=chunks,
                                      source_metadata={"profile": sample["profile_version"], "chunking": "short-heading1-v1"})
    # 字符数不等于 Token 数，提前检查，避免 SentenceTransformer 在编码时静默截断章节。
    tokenized = load_embedding_model().tokenizer([chunk["content"] for chunk in chunks],
                                                add_special_tokens=True, truncation=False)
    token_counts = [len(tokens) for tokens in tokenized["input_ids"]]
    if any(count > config["max_seq_length"] for count in token_counts):
        raise DocumentParseError("片段超过 Embedding 输入容量，需要先更细切分")
    vectors = embed_documents([chunk["content"] for chunk in chunks])
    return {"document": document, "manifest": manifest, "chunks": chunks, "vectors": vectors}, config, sample, token_counts


def run_case(case_id, source, access, top_k, run_chat):
    case = CASES[case_id]
    record = {"case_id": case_id, **case, "top_k": top_k, "manual_review": "pending",
              "chat_attempted": False, "raw_content": None, "actual": None, "citations": None}
    stage = "retrieval"
    try:
        started = time.perf_counter()
        prepared = prepare_authorized_rag_request(case["question"], source, access, top_k)
        record.update(prepared)
        record["retrieval_elapsed_ms"] = round((time.perf_counter() - started) * 1000)
        print(f"\n[{case_id}] {case['question']}", flush=True)
        for hit in prepared["retrieved_chunks"]:
            location = hit["chunk"]["locator"]
            print(f"  检索：{hit['chunk']['id']}，score={hit['score']:.4f}，章节={location['section']}，正文块={location['block_start']}-{location['block_end']}", flush=True)
        if not run_chat:
            print(json.dumps(prepared["messages"], ensure_ascii=False, indent=2))
            record["status"] = "preview"
            return record
        stage = "call"
        record["chat_attempted"] = True
        record["raw_content"] = tracked_model_call(prepared["messages"], record, prompt_version=PROMPT_VERSION)
        stage = "parse"
        record["actual"] = parse_policy_answer(record["raw_content"], prepared["documents"])
        stage = "citations"
        record["citations"] = resolve_citations(record["actual"]["sources"], prepared["retrieved_chunks"])
        sections = {item["locator"]["section"] for item in record["citations"]}
        record["objective_checks"] = {"expected_answerability": record["actual"]["canAnswer"] == case["expected_can_answer"],
                                      "required_sections_cited": set(case["required_sections"]).issubset(sections)}
        record["status"] = "completed"
        print(json.dumps({**record["actual"], "citations": record["citations"]}, ensure_ascii=False, indent=2), flush=True)
        print(f"  可回答性/必要章节核对：{record['objective_checks']}；语义仍需对照原文。", flush=True)
    except Exception as error:
        record.update(status="error", error_stage=stage, error_type=type(error).__name__)
        if isinstance(getattr(error, "status_code", None), int):
            record["http_status"] = error.status_code
        print(f"  失败阶段：{stage}；异常类型：{type(error).__name__}", flush=True)
    return record


def run(args):
    now = datetime.now(timezone(timedelta(hours=8)))
    source = "day9-docx-live-" + uuid4().hex
    record = {"run_time": now.isoformat(), "source_id": source, "prompt_version": PROMPT_VERSION,
              "mode": "run" if args.run else "preview", "real_embedding": False, "real_chat_model": False,
              "setup_complete": False, "teaching_data_cleaned": False, "cases": [], "manual_review_required": True,
              "limitations": "单份短 Word 制度，三个片段；不是通用 Word/长表解析或大库检索评估，身份仍由教学脚本模拟。"}
    try:
        prepared_word, config, sample, token_counts = prepare_word(args.profile)
        record.update(real_embedding=True, embedding=config, document=prepared_word["document"],
                      raw_blocks=sample["raw_blocks"], chunks=prepared_word["chunks"],
                      profile_version=sample["profile_version"], token_counts=token_counts)
        with connect_database() as connection:
            with connection.transaction():
                connection.execute((PROJECT_ROOT / "infra/document_sync_schema.sql").read_text(encoding="utf-8"), prepare=False)
            register_vector(connection)
            try:
                with connection.transaction():
                    connection.execute("INSERT INTO leave_assistant_lab.synced_sources (id) VALUES (%s)", (source,))
                identifier = prepared_word["document"]["id"]
                batch = {"source_id": source, "expected_generation": 0, "embedding_config": config,
                         "operations": plan_document_sync([], [prepared_word["manifest"]], complete_snapshot=True),
                         "documents": {identifier: prepared_word}}
                record["sync_result"] = apply_sync_batch(connection, batch)
                stored = connection.execute("SELECT id,locator FROM leave_assistant_lab.synced_chunks WHERE source_id=%s", (source,)).fetchall()
                if {row["id"]: row["locator"] for row in stored} != {chunk["id"]: chunk["locator"] for chunk in prepared_word["chunks"]}:
                    raise ValueError("章节定位入库后发生变化")
                record["setup_complete"] = True
                print(f"Word已解析并真实编码入库：{len(prepared_word['chunks'])}个片段，Token数={token_counts}。", flush=True)
                access = TrustedAccessContext("day9-demo-engineer", (source,), ("engineering",))
                for case_id in CASES if args.suite else [args.case]:
                    result = run_case(case_id, source, access, args.top_k, args.run)
                    record["cases"].append(result)
                    if result.get("error_stage") == "call":
                        print("模型调用失败，停止后续题目，不自动重试。", flush=True)
                        break
                record["real_chat_model"] = any(item["raw_content"] is not None for item in record["cases"])
                record["chat_attempt_count"] = sum(item["chat_attempted"] for item in record["cases"])
            finally:
                with connection.transaction():
                    connection.execute("DELETE FROM leave_assistant_lab.synced_documents WHERE source_id=%s", (source,))
                    connection.execute("DELETE FROM leave_assistant_lab.synced_sources WHERE id=%s", (source,))
                record["teaching_data_cleaned"] = connection.execute(
                    "SELECT count(*) AS count FROM leave_assistant_lab.synced_sources WHERE id=%s", (source,)
                ).fetchone()["count"] == 0
    except Exception as error:
        record["setup_error_type"] = type(error).__name__
        print(f"运行中止：{type(error).__name__}；请结合 setup_complete 与报告定位。", flush=True)
        if isinstance(error, FileNotFoundError):
            record["missing_file"] = str(error.filename)
            print(f"缺少文件：{error.filename}", flush=True)
    path = PROJECT_ROOT / "reports" / f"docx-rag-live-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告：{path}")
    print(f"教学来源清理：{record['teaching_data_cleaned']}；未写原 policy-dev 或替换 PDF 样例。")
    if not args.run:
        print(f"仅预览：实际本地编码={record['real_embedding']}，数据库准备完成={record['setup_complete']}；未调用聊天模型。")
    expected = len(CASES) if args.suite else 1
    completed = len(record["cases"]) == expected and all(item["status"] != "error" for item in record["cases"])
    checks_ok = all(all(item.get("objective_checks", {}).values()) for item in record["cases"])
    return 0 if record["setup_complete"] and record["teaching_data_cleaned"] and completed and checks_ok else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(CASES), default="city_limits")
    parser.add_argument("--suite", action="store_true")
    parser.add_argument("--profile", help="登记配置 JSON 路径；source_file 相对该配置所在目录解析")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--run", action="store_true", help="每题一次真实 DeepSeek 调用，整套最多三次")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k 必须至少为1")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
