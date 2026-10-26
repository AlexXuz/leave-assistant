"""Run public Agent practice cases against a learner-owned async adapter."""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
from pathlib import Path

from app.course.agent_evaluation import evaluate_suite, load_suite
from app.paths import PROJECT_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", default="course.projects.support_agent_runtime:evaluate_case")
    parser.add_argument("--suite", type=Path, default=PROJECT_ROOT / "course/fixtures/agent_cases.json")
    parser.add_argument("--mode", choices=("offline", "live"), default="offline", help="Operator label only; adapter owns model calls and costs")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports/learner/agent-evaluation.json")
    args = parser.parse_args(argv)
    try:
        module, separator, symbol = args.adapter.partition(":")
        if not separator or not module or not symbol:
            raise ValueError("adapter must be module:function")
        adapter = getattr(importlib.import_module(module), symbol)
        suite, digest = load_suite(args.suite)
        report = asyncio.run(evaluate_suite(adapter, suite, suite_sha256=digest, repeats=args.repeats, mode=args.mode))
        report["adapter"] = args.adapter
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError, ImportError, AttributeError, TypeError) as error:
        # Do not print arbitrary exception messages from imported learner code.
        print(json.dumps({"status": "evaluation_setup_failed", "error_type": type(error).__name__}, ensure_ascii=False))
        return 2
    print(json.dumps({"report": str(args.output.resolve()), "summary": report["summary"], "completion_eligible": False}, ensure_ascii=False))
    return 0 if report["summary"]["checks_passed"] == report["summary"]["trial_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
