"""Day 8 收尾：真实 PDF/Embedding/pgvector/引用；默认预览，--run 才调用 DeepSeek。"""

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
import os
import time
from uuid import uuid4

from pgvector.psycopg import register_vector

from app.document_manifest import build_document_manifest
from app.document_sync import plan_document_sync
from app.document_sync_execution import apply_sync_batch
from app.embeddings import embed_documents
from app.exercises import call_model
from app.located_chunking import split_located_pages
from app.pdf_preparation import prepare_sample_pdf
from app.permission_rag import prepare_authorized_rag_request
from app.permission_service import TrustedAccessContext
from app.pgvector_store import PROJECT_ROOT, connect_database
from app.policy_qa import parse_policy_answer
from app.source_citations import resolve_citations
from app.vector_index import current_embedding_config

PROMPT_VERSION = "pdf-policy-rag-v1"
CASES = {
    "lodging": {"question": "去上海出差，住宿每晚最多报销多少元？超过上限要提前取得谁的什么批准？",
                "expected_can_answer": True, "required_pages": [1],
                "manual_check": "核对城市、每人每晚的金额，以及预订前/部门经理/书面批准是否完整。"},
    "combined": {"question": "去上海出差，住宿每晚报销上限是多少？报销住宿费用需要提交哪些凭证？",
                 "expected_can_answer": True, "required_pages": [1, 2],
                 "manual_check": "核对住宿金额与两种凭证，确认两部分事实分别得到原页支持。"},
    "unknown": {"question": "出差每天的餐费补贴是多少元？",
                "expected_can_answer": False, "required_pages": [],
                "manual_check": "文件未规定金额，应说明资料不足，不能猜测补贴标准。"},
}


def prepare_pdf():
    sample = prepare_sample_pdf()
    chunks = split_located_pages(sample["document"], sample["pages"])
    document = {**sample["document"], "content": "\n\n".join(page["text"] for page in sample["pages"]),
                "visibility": "department", "allowed_departments": ["engineering"]}
    config = current_embedding_config()
    manifest = build_document_manifest(document, config, chunks=chunks, source_metadata={
        "cleaning_profile": sample["profile_version"], "chunking": {"max_chars": 200, "overlap": 30}})
    vectors = embed_documents([chunk["content"] for chunk in chunks])
    return {"document": document, "manifest": manifest, "chunks": chunks, "vectors": vectors}, config, sample


def tracked_model_call(messages, record, *, prompt_version=PROMPT_VERSION):
    # 单线程教学 CLI 捕获现有 call_model 的用量日志，保留其原接口，不修改学生函数。
    captured = StringIO()
    started = time.perf_counter()
    try:
        with redirect_stdout(captured):
            return call_model(messages, prompt_version=prompt_version)
    finally:
        record["chat_elapsed_ms"] = round((time.perf_counter() - started) * 1000)
        record["configured_model"] = os.getenv("LLM_MODEL")
        record["model_metadata"] = None
        for line in captured.getvalue().splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and "latency_ms" in value:
                record["model_metadata"] = {key: value.get(key) for key in
                    ("model", "prompt_version", "latency_ms", "finish_reason", "tokens")}


def run_case(case_id, source_id, access, top_k, run_chat):
    case = CASES[case_id]
    record = {"case_id": case_id, "question": case["question"], "top_k": top_k,
              "expected_can_answer": case["expected_can_answer"], "required_pages": case["required_pages"],
              "manual_check": case["manual_check"], "manual_review": "pending", "chat_attempted": False,
              "raw_content": None, "actual": None, "citations": None}
    stage = "retrieval"
    try:
        started = time.perf_counter()
        prepared = prepare_authorized_rag_request(case["question"], source_id, access, top_k)
        record["retrieval_elapsed_ms"] = round((time.perf_counter() - started) * 1000)
        record.update(prepared)
        print(f"\n[{case_id}] {case['question']}", flush=True)
        for hit in prepared["retrieved_chunks"]:
            print(f"  检索：{hit['chunk']['id']}，score={hit['score']:.4f}，页码={hit['chunk']['locator']['page']}", flush=True)
        if not run_chat:
            print(json.dumps(prepared["messages"], ensure_ascii=False, indent=2))
            record["status"] = "preview"
            return record
        stage = "call"
        record["chat_attempted"] = True
        record["raw_content"] = tracked_model_call(prepared["messages"], record)
        stage = "parse"
        record["actual"] = parse_policy_answer(record["raw_content"], prepared["documents"])
        stage = "citations"
        record["citations"] = resolve_citations(record["actual"]["sources"], prepared["retrieved_chunks"])
        cited_pages = {citation["locator"]["page"] for citation in record["citations"]}
        record["objective_checks"] = {
            "expected_answerability": record["actual"]["canAnswer"] == case["expected_can_answer"],
            "required_pages_cited": set(case["required_pages"]).issubset(cited_pages),
        }
        record["status"] = "completed"
        print(json.dumps({**record["actual"], "citations": record["citations"]}, ensure_ascii=False, indent=2), flush=True)
        print(f"  结构/引用存在性通过；可回答性与必要页核对：{record['objective_checks']}。正文语义待人工复核。", flush=True)
    except Exception as error:
        # 不输出认证信息、连接串或完整供应商异常；保留失败阶段，禁止无权限回退/自动重试。
        record.update(status="error", error_stage=stage, error_type=type(error).__name__)
        if isinstance(getattr(error, "status_code", None), int):
            record["http_status"] = error.status_code
        print(f"  失败阶段：{stage}；异常类型：{type(error).__name__}", flush=True)
    return record


def run(args):
    now = datetime.now(timezone(timedelta(hours=8)))
    record = {"run_time": now.isoformat(), "prompt_version": PROMPT_VERSION, "mode": "run" if args.run else "preview",
              "real_embedding": False, "real_chat_model": False, "cases": [], "setup_complete": False,
              "teaching_data_cleaned": False, "manual_review_required": True,
              "limitations": "两页两片段的教学文档，Top-2会取回全部可见片段；本次不代表大库检索或生产可靠性评估。"}
    source_id = "day8-pdf-live-" + uuid4().hex
    record["source_id"] = source_id
    try:
        prepared_pdf, config, sample = prepare_pdf()
        record["real_embedding"] = True
        record.update(embedding=config, document=prepared_pdf["document"], profile_version=sample["profile_version"],
                      raw_pages=sample["raw_pages"], cleaned_pages=sample["pages"], chunk_count=len(prepared_pdf["chunks"]))
        with connect_database() as connection:
            with connection.transaction():
                connection.execute((PROJECT_ROOT / "infra/document_sync_schema.sql").read_text(encoding="utf-8"), prepare=False)
            register_vector(connection)
            try:
                with connection.transaction():
                    connection.execute("INSERT INTO leave_assistant_lab.synced_sources (id) VALUES (%s)", (source_id,))
                document_id = prepared_pdf["document"]["id"]
                batch = {"source_id": source_id, "expected_generation": 0, "embedding_config": config,
                         "operations": plan_document_sync([], [prepared_pdf["manifest"]], complete_snapshot=True),
                         "documents": {document_id: prepared_pdf}}
                record["sync_result"] = apply_sync_batch(connection, batch)
                record["setup_complete"] = True
                print(f"真实 PDF 已编码并提交：片段{len(prepared_pdf['chunks'])}条；独立来源 {source_id}", flush=True)
                access = TrustedAccessContext("day8-demo-engineer", (source_id,), ("engineering",))
                for case_id in CASES if args.suite else [args.case]:
                    case_record = run_case(case_id, source_id, access, args.top_k, args.run)
                    record["cases"].append(case_record)
                    if case_record.get("error_stage") == "call":
                        print("模型调用失败，停止后续题目；不自动重试。", flush=True)
                        break
                record["real_chat_model"] = any(case["raw_content"] is not None for case in record["cases"])
                record["chat_attempt_count"] = sum(case["chat_attempted"] for case in record["cases"])
            finally:
                with connection.transaction():
                    connection.execute("DELETE FROM leave_assistant_lab.synced_documents WHERE source_id=%s", (source_id,))
                    connection.execute("DELETE FROM leave_assistant_lab.synced_sources WHERE id=%s", (source_id,))
                record["teaching_data_cleaned"] = connection.execute(
                    "SELECT count(*) AS count FROM leave_assistant_lab.synced_sources WHERE id=%s", (source_id,)
                ).fetchone()["count"] == 0
    except Exception as error:
        record.update(setup_error_type=type(error).__name__)
        print(f"运行中止：{type(error).__name__}；请结合 setup_complete 与报告定位。", flush=True)
    directory = PROJECT_ROOT / "reports"
    directory.mkdir(exist_ok=True)
    path = directory / f"pdf-rag-live-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告：{path}")
    print(f"教学来源清理：{record['teaching_data_cleaned']}；原 policy-dev 未参与写入。")
    if not args.run:
        print("仅预览：使用真实本地 Embedding 和数据库，未调用聊天模型。")
    expected_count = len(CASES) if args.suite else 1
    completed = len(record["cases"]) == expected_count and all(case["status"] != "error" for case in record["cases"])
    checks_ok = all(all(case.get("objective_checks", {}).values()) for case in record["cases"])
    return 0 if record["setup_complete"] and record["teaching_data_cleaned"] and completed and checks_ok else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(CASES), default="lodging")
    parser.add_argument("--suite", action="store_true", help="运行固定的单页/两页/资料不足三题")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--run", action="store_true", help="每题调用一次现有 DeepSeek API；整套最多三次")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k 必须至少为1")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
