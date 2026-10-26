"""Evidence-based teaching checks; neither a model judge nor a completion certificate."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
from pathlib import Path
import time
from typing import Callable

from app.course.agent_lab import ToolSandbox


def load_suite(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    suite = json.loads(raw)
    if suite.get("schema_version") != 1 or not isinstance(suite.get("world"), dict):
        raise ValueError("Unsupported Agent suite")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Suite needs cases")
    ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("case_id must be nonempty and unique")
    for case in cases:
        if not isinstance(case.get("task"), str) or not isinstance(case.get("expected"), dict):
            raise ValueError("Each case needs task and expected")
    return suite, hashlib.sha256(raw).hexdigest()


def _usage(value: object) -> dict:
    value = value if isinstance(value, dict) else {}
    return {
        key: value[key] if type(value.get(key)) is int and value[key] >= 0 else None
        for key in ("prompt_tokens", "completion_tokens")
    }


def grade_trial(output: object, audit: list[dict], expected: dict, *, budget_exhausted: bool = False) -> dict:
    """Check independently observed tool results; answer semantics remain manual.

    Requirements use evidence and tool sets, not an exact trajectory, so valid
    alternative action orders are not penalized. Test cases are public practice.
    """
    failures: list[str] = []
    if not isinstance(output, dict):
        return {"status": "failed", "checks_passed": False, "failures": ["adapter_output_must_be_object"], "task_success": None}
    if output.get("status") not in expected.get("allowed_statuses", []):
        failures.append("unexpected_terminal_status")
    if not isinstance(output.get("answer"), str) or not output["answer"].strip():
        failures.append("missing_answer_or_user_question")
    claimed = output.get("evidence_ids")
    if not isinstance(claimed, list) or any(not isinstance(x, str) for x in claimed):
        failures.append("invalid_evidence_ids")
        claimed = []
    observed_evidence = {eid for event in audit for eid in event["result"].get("evidence_ids", [])}
    if not set(claimed).issubset(observed_evidence):
        failures.append("evidence_not_observed_in_tool_results")
    if not set(expected.get("required_evidence", [])).issubset(set(claimed)):
        failures.append("required_evidence_missing")
    observed_tools = {event["tool"] for event in audit}
    if not set(expected.get("required_tools", [])).issubset(observed_tools):
        failures.append("required_tool_observation_missing")
    if observed_tools.intersection(expected.get("forbidden_tools", [])):
        failures.append("forbidden_tool_attempt")
    observed_errors = {event["result"].get("error", {}).get("code") for event in audit}
    if not set(expected.get("required_error_codes", [])).issubset(observed_errors):
        failures.append("required_failure_not_exercised")
    if budget_exhausted:
        failures.append("tool_budget_exhausted")
    if type(output.get("model_calls")) is not int or output["model_calls"] < 0:
        failures.append("invalid_reported_model_call_count")
    return {
        "status": "failed" if failures else "manual_review_required",
        "checks_passed": not failures,
        "failures": failures,
        "task_success": None,
        "semantic_review": "Check answer against evidence, task intent and final state; no automatic semantic pass.",
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]


async def evaluate_suite(adapter: Callable, suite: dict, *, suite_sha256: str, repeats: int = 3, mode: str = "offline") -> dict:
    if type(repeats) is not int or not 1 <= repeats <= 20:
        raise ValueError("repeats must be 1..20")
    if mode not in {"offline", "live"}:
        raise ValueError("mode must be offline or live")
    started_at = datetime.now(timezone.utc).isoformat()
    trials = []
    for case in suite["cases"]:
        limits = {"max_tool_calls": 8, "total_seconds": 30.0, **case.get("limits", {})}
        seconds = limits["total_seconds"]
        if type(seconds) not in {int, float} or not 0 < seconds <= 300:
            raise ValueError("total_seconds must be in (0, 300]")
        for repeat in range(1, repeats + 1):
            tools = ToolSandbox(suite["world"], case.get("fixture", {}), user_id=case.get("user_id", "customer-a"), max_calls=limits["max_tool_calls"])
            public_case = {"case_id": case["case_id"], "task": case["task"], "inputs": deepcopy(case.get("inputs", {})), "limits": deepcopy(limits)}
            started = time.monotonic()
            output = None
            failure = None
            try:
                async with asyncio.timeout(seconds):
                    pending = adapter(public_case, tools)
                    if not inspect.isawaitable(pending):
                        raise TypeError("Adapter must return an awaitable")
                    output = await pending
            except NotImplementedError:
                failure = "learner_adapter_not_implemented"
            except TimeoutError:
                failure = "trial_deadline_exceeded"
            except Exception as error:
                # Avoid logging arbitrary adapter exceptions containing credentials.
                failure = "adapter_error:" + type(error).__name__
            elapsed = round((time.monotonic() - started) * 1000, 3)
            audit = tools.audit
            grade = grade_trial(output, audit, case["expected"], budget_exhausted=tools.budget_exhausted)
            if failure:
                grade.update(status="failed", checks_passed=False, failures=[failure], task_success=None)
            reported = output if isinstance(output, dict) else {}
            trials.append({
                "case_id": case["case_id"], "repeat": repeat, "duration_ms": elapsed,
                "grade": grade, "tool_audit": audit,
                "adapter_reported": {
                    "status": reported.get("status"), "answer": reported.get("answer"),
                    "evidence_ids": reported.get("evidence_ids"), "model_calls": reported.get("model_calls"),
                    "usage": _usage(reported.get("usage")),
                    "model": reported.get("model"), "prompt_version": reported.get("prompt_version"),
                },
                "model_execution_verified": False,
            })
    durations = [trial["duration_ms"] for trial in trials]
    usage_known = sum(all(value is not None for value in trial["adapter_reported"]["usage"].values()) for trial in trials)
    tool_events = [event for trial in trials for event in trial["tool_audit"]]
    return {
        "kind": "agent_practice_evaluation", "schema_version": 1,
        "started_at": started_at,
        "mode": mode, "mode_is_operator_label_not_proof_of_model_execution": True,
        "suite_sha256": suite_sha256, "public_practice_cases": True, "repeats": repeats,
        "completion_eligible": False,
        "summary": {
            "trial_count": len(trials),
            "checks_passed": sum(trial["grade"]["checks_passed"] for trial in trials),
            "tool_evidence_check_rate": sum(trial["grade"]["checks_passed"] for trial in trials) / len(trials),
            "task_success_rate": None,
            "tool_call_count": len(tool_events),
            "tool_error_count": sum(event["result"]["status"] == "error" for event in tool_events),
            "authorization_denial_count": sum(event["result"].get("error", {}).get("code") == "ACCESS_DENIED" for event in tool_events),
            "forbidden_tool_attempt_trials": sum("forbidden_tool_attempt" in trial["grade"]["failures"] for trial in trials),
            "deadline_failure_trials": sum("trial_deadline_exceeded" in trial["grade"]["failures"] for trial in trials),
            "manual_review_required": sum(trial["grade"]["status"] == "manual_review_required" for trial in trials),
            "latency_ms": {"p50": _percentile(durations, .5), "p95": _percentile(durations, .95)},
            "usage_complete_trials_reported": usage_known,
            "usage_unknown_trials": len(trials) - usage_known,
            "cost": None, "cost_status": "unknown_requires_verified_usage_and_dated_provider_pricing",
        },
        "limitations": [
            "Tool audit verifies this local synthetic API only; it does not prove production security.",
            "Adapter output and model usage are self-reported; review actual provider traces separately.",
            "No model judge is run. Correct evidence IDs do not establish correct interpretation.",
            "Public fixtures are not unseen tasks. A reviewer must supply new requirements.",
            "Async deadlines require cooperative code; blocking or hostile adapters need process isolation.",
            "Tool counts are recorded attempts, capped at the per-trial tool budget plus one rejection.",
        ],
        "trials": trials,
    }
