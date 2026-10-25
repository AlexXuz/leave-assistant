"""制度问答运行器。默认只预览消息；只有 --run 会发起一次真实调用。"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.course.examples.foundations.exercises import call_model
from app.course.examples.foundations.policy_qa import (
    POLICY_PROMPT_VERSION,
    build_policy_messages,
    load_policy_documents,
    parse_policy_answer,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="企业制度问答：默认只预览消息")
    parser.add_argument("--case", default="annual_four_days")
    parser.add_argument("--mode", choices=("direct", "context"), default="context")
    parser.add_argument("--run", action="store_true", help="发起一次真实模型调用")
    args = parser.parse_args(argv)
    cases = json.loads((PROJECT_ROOT / "data/policy_questions.json").read_text(encoding="utf-8"))
    case = next((item for item in cases if item["id"] == args.case), None)
    if case is None:
        parser.error("未知 case；可选：" + ", ".join(item["id"] for item in cases))
    documents = load_policy_documents() if args.mode == "context" else []
    try:
        messages = build_policy_messages(case["question"], documents)
    except NotImplementedError as error:
        print(f"尚未调用模型：{error}")
        return 2
    if not args.run:
        print(json.dumps(messages, ensure_ascii=False, indent=2))
        print(f"预览完成；mode={args.mode}，文档数={len(documents)}；零模型调用")
        return 0

    now = datetime.now(timezone(timedelta(hours=8)))
    # 两组都遵守同一证据规则。无文档时，预期拒答，而非要求模型猜测。
    expected = case["expected"] if documents else {
        "canAnswer": False,
        "sources": [],
        "answer_points": ["没有提供公司制度，资料不足，不能猜测"],
    }
    record = {
        "run_time": now.isoformat(), "id": case["id"], "mode": args.mode,
        "prompt_version": POLICY_PROMPT_VERSION,
        "messages": messages, "expected": expected,
        "raw_content": None, "actual": None,
        "manual_review_required": True,
    }
    stage = "call"
    try:
        record["raw_content"] = call_model(messages, prompt_version=POLICY_PROMPT_VERSION)
        stage = "parse"
        record["actual"] = parse_policy_answer(record["raw_content"], documents)
        record["structure_valid"] = True
    except Exception as error:
        record.update(structure_valid=False, error_stage=stage, error_type=type(error).__name__)
    record["configured_model"] = os.getenv("LLM_MODEL")
    reports = PROJECT_ROOT / "reports"
    reports.mkdir(exist_ok=True)
    path = reports / f"policy-{now.strftime('%Y%m%d-%H%M%S-%f')}-{args.mode}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record.get("actual"), ensure_ascii=False, indent=2))
    if "error_type" in record:
        print(f"失败阶段：{record['error_stage']}；异常类型：{record['error_type']}")
    print(f"报告：{path}")
    print("结构有效不代表语义正确；请人工核对回答、引用依据及拒答是否恰当。")
    return 0 if record["structure_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
