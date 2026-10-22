"""教学评测骨架：先实现 compare_result，再实现 classify_error。

默认预览：python -m scripts.evaluate_leave
本地比较检查：python -m scripts.evaluate_leave --check
真实评测：python -m scripts.evaluate_leave --run
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import ValidationError

from app.exercises import PROMPT_VERSION, build_messages, call_model, parse_model_output

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = PROJECT_ROOT / "data" / "eval_cases.json"
CHECK_NAMES = {"leaveType", "startDate", "endDate", "reason_is_missing", "missingFields"}


def compare_result(actual: dict, expected: dict) -> dict[str, bool]:
    """作业 1：返回五项客观检查，每个值为 bool。

    leaveType/startDate/endDate：实际值与预期值精确相等。
    reason_is_missing：实际理由是否为 None，与预期是否为 None 相同。
    missingFields：比较字段名集合，忽略排列顺序。

    理由非空时的语义不在此函数中自动评分，由人工复核。
    不修改 actual 和 expected。
    """
    result = {
        "leaveType": actual["leaveType"] == expected["leaveType"],
        "startDate": actual["startDate"] == expected["startDate"],
        "endDate": actual["endDate"] == expected["endDate"],
        "reason_is_missing": (actual["reason"] is None) == (expected["reason"] is None),
        "missingFields": set(actual["missingFields"]) == set(expected["missingFields"])
    }
    return result


def classify_error(error: Exception, stage: str) -> str:
    """作业 2：按失败阶段与异常类型返回类别。

    stage == "call"：CALL_ERROR（仅说明模型调用函数失败，根因另查）。
    stage == "parse"：
      JSONDecodeError -> JSON_PARSE_ERROR
      ValidationError -> SCHEMA_ERROR
      其他 ValueError -> BUSINESS_RULE_ERROR
      其他异常 -> UNEXPECTED_ERROR
    其他 stage：UNEXPECTED_ERROR。

    注意 JSONDecodeError/ValidationError 都属于 ValueError，判断顺序要正确。
    """
    message = "UNEXPECTED_ERROR"
    if stage == "call":
        message = "CALL_ERROR"
    if stage == "parse":
        if isinstance(error, json.JSONDecodeError):
            message = "JSON_PARSE_ERROR"
        elif isinstance(error, ValidationError):
            message = "SCHEMA_ERROR"
        elif isinstance(error, ValueError):
            message = "BUSINESS_RULE_ERROR"



    return message


# 以下是已提供的文件读取、批量执行、报告保存骨架。
def load_cases(path: Path = CASES_PATH) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list) or not cases:
        raise ValueError("评测数据必须是非空列表")
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("用例 id 不得重复")
    return cases


def checked_comparison(actual: dict, expected: dict) -> dict[str, bool]:
    checks = compare_result(actual, expected)
    if not isinstance(checks, dict) or set(checks) != CHECK_NAMES:
        raise ValueError("compare_result 必须返回约定的五项检查")
    if any(type(value) is not bool for value in checks.values()):
        raise ValueError("每项检查结果必须为 bool")
    return checks


def check_comparison(cases: list[dict]) -> None:
    expected = cases[0]["expected"]
    correct = checked_comparison(dict(expected), expected)
    if not all(correct.values()):
        raise ValueError("相同结果应当全部通过")

    wrong_date = dict(expected)
    wrong_date["startDate"] = "2026-10-19"
    date_checks = checked_comparison(wrong_date, expected)
    if date_checks["startDate"]:
        raise ValueError("必须识别开始日期不符合预期")

    missing_reason = dict(expected)
    missing_reason["reason"] = None
    missing_reason["missingFields"] = ["reason"]
    reason_checks = checked_comparison(missing_reason, expected)
    if reason_checks["reason_is_missing"] or reason_checks["missingFields"]:
        raise ValueError("必须识别理由空值状态与缺失列表不符合预期")
    print("本地比较检查通过；未调用模型")


def evaluate_case(case: dict) -> dict:
    record = {
        "id": case["id"],
        "input": case["input"],
        "expected": case["expected"],
        "messages": None,
        "raw_content": None,
        "actual": None,
        "call_ok": False,
        "validation_ok": False,
        "field_checks": None,
        "passed": False,
        "error_category": None,
        "reason_review_required": False,
    }
    stage = "build"
    started = time.perf_counter()
    try:
        messages = build_messages(case["input"]["text"], case["input"]["referenceTime"])
        record["messages"] = messages
        stage = "call"
        record["raw_content"] = call_model(messages)
        record["call_ok"] = True

        stage = "parse"
        record["actual"] = parse_model_output(record["raw_content"])
        record["validation_ok"] = True
        record["reason_review_required"] = (
            record["actual"]["reason"] is not None
            and case["expected"]["reason"] is not None
        )

        stage = "compare"
        record["field_checks"] = checked_comparison(record["actual"], case["expected"])
        record["passed"] = all(record["field_checks"].values())
        if not record["passed"]:
            record["error_category"] = "ANSWER_MISMATCH"
    except NotImplementedError:
        raise
    except Exception as error:
        record["error_category"] = classify_error(error, stage)
        record["error_stage"] = stage
        record["error_type"] = type(error).__name__
    finally:
        record["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="请假提取教学评测")
    parser.add_argument(
        "--cases", type=Path, default=CASES_PATH,
        help="评测数据文件；默认使用 Day 2 的十二条基线",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="本地验证 compare_result")
    modes.add_argument("--run", action="store_true", help="逐条调用真实模型并保存报告")
    args = parser.parse_args(argv)
    cases = load_cases(args.cases)

    if not args.check and not args.run:
        print(f"已读取 {len(cases)} 条用例，Prompt：{PROMPT_VERSION}")
        for case in cases:
            print(f"{case['id']}: {case['input']['text']}")
        print("先完成 compare_result，再使用 --check；完成 classify_error 后使用 --run")
        return 0

    try:
        check_comparison(cases)
        if args.check:
            return 0
        # 真实调用前，确认第二个作业函数也已实现。
        if classify_error(ValueError("本地调用阶段示例"), "call") != "CALL_ERROR":
            raise ValueError("调用阶段异常应分类为 CALL_ERROR")
    except (NotImplementedError, ValueError) as error:
        print(f"尚未开始真实评测：{error}")
        return 2

    results = []
    for case in cases:
        print(f"\n正在评测：{case['id']}", flush=True)
        result = evaluate_case(case)
        results.append(result)
        print(f"客观字段通过：{result['passed']}；失败类别：{result['error_category']}", flush=True)

    summary = {
        "total": len(results),
        "call_ok": sum(result["call_ok"] for result in results),
        "validation_ok": sum(result["validation_ok"] for result in results),
        "objective_passed": sum(result["passed"] for result in results),
        "reason_reviews_pending": sum(result["reason_review_required"] for result in results),
    }
    run_time = datetime.now(timezone(timedelta(hours=8)))
    report = {
        "run_time": run_time.isoformat(),
        "cases_file": str(args.cases.resolve()),
        "configured_model": os.getenv("LLM_MODEL"),
        "prompt_version": PROMPT_VERSION,
        "grading_note": "passed 仅表示客观字段检查通过，非空理由语义需人工复核",
        "summary": summary,
        "results": results,
    }
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"evaluation-{run_time.strftime('%Y%m%d-%H%M%S-%f')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n汇总：", json.dumps(summary, ensure_ascii=False))
    print("报告：", report_path)
    return 0 if summary["objective_passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
