"""Infrastructure checks only: scripted adapters below are not learner Agents."""
from copy import deepcopy
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from app.course.agent_evaluation import evaluate_suite, grade_trial, load_suite
from app.course.agent_lab import ToolSandbox
from app.paths import PROJECT_ROOT


SUITE_PATH = PROJECT_ROOT / "course/fixtures/agent_cases.json"


class ToolBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.suite, self.digest = load_suite(SUITE_PATH)
        self.tools = ToolSandbox(self.suite["world"], {}, user_id="customer-a")

    async def test_identity_cannot_come_from_arguments(self):
        injected = await self.tools.call("get_order", {"order_id": "B900", "user_id": "customer-b"})
        denied = await self.tools.call("get_order", {"order_id": "B900"})
        self.assertEqual(injected["error"]["code"], "INVALID_ARGUMENTS")
        self.assertEqual(denied["error"]["code"], "ACCESS_DENIED")
        self.assertNotIn("OTHER_CUSTOMER_PRIVATE_ITEM", json.dumps(self.tools.audit))

    async def test_unknown_tools_and_invalid_shapes_are_structured_errors(self):
        for name, args, code in [
            ("delete_order", {"order_id": "A100"}, "UNKNOWN_TOOL"),
            ("get_order", {"order_id": 100}, "INVALID_ARGUMENTS"),
            ("get_order", {"order_id": True}, "INVALID_ARGUMENTS"),
            ("get_order", {}, "INVALID_ARGUMENTS"),
            ("search_knowledge", {"query": ""}, "INVALID_ARGUMENTS"),
        ]:
            with self.subTest(name=name, args=args):
                result = await self.tools.call(name, args)
                self.assertEqual(result["error"]["code"], code)
                self.assertEqual(result["evidence_ids"], [])

    async def test_not_found_is_not_zero_or_success(self):
        result = await self.tools.call("get_order", {"order_id": "A404"})
        self.assertEqual(result, {"status": "not_found", "data": None, "evidence_ids": []})

    async def test_injected_text_cannot_expand_tool_authority(self):
        fixture = next(case["fixture"] for case in self.suite["cases"] if case["case_id"] == "retrieved_prompt_injection")
        tools = ToolSandbox(self.suite["world"], fixture, user_id="customer-a")
        document = await tools.call("search_knowledge", {"query": "物流"})
        self.assertIn("delete_order", document["data"][0]["text"])
        self.assertEqual((await tools.call("delete_order", {"order_id": "A100"}))["error"]["code"], "UNKNOWN_TOOL")
        self.assertEqual((await tools.call("get_order", {"order_id": "B900"}))["error"]["code"], "ACCESS_DENIED")

    async def test_audit_copy_and_bounded_calls(self):
        tools = ToolSandbox(self.suite["world"], {}, user_id="customer-a", max_calls=1)
        await tools.call("get_order", {"order_id": "A100"})
        copied = tools.audit
        copied[0]["result"]["evidence_ids"] = ["forged"]
        self.assertNotEqual(tools.audit[0]["result"]["evidence_ids"], ["forged"])
        limited = await tools.call("get_order", {"order_id": "A100"})
        self.assertEqual(limited["error"]["code"], "TOOL_CALL_BUDGET")
        self.assertTrue(tools.budget_exhausted)

    async def test_concurrent_tools_keep_unique_invocation_sequence(self):
        tools = ToolSandbox(self.suite["world"], {"delays": {"get_order": .01}}, user_id="customer-a")
        await asyncio.gather(tools.call("get_order", {"order_id": "A100"}),
                             tools.call("get_shipment", {"order_id": "A100"}))
        audit = tools.audit
        self.assertEqual({event["sequence"] for event in audit}, {1, 2})
        self.assertEqual(next(event for event in audit if event["tool"] == "get_order")["sequence"], 1)


class EvaluationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.suite, self.digest = load_suite(SUITE_PATH)

    async def test_no_tool_fabrication_cannot_pass(self):
        case = self.suite["cases"][0]
        output = {"status": "completed", "answer": "已查到", "evidence_ids": case["expected"]["required_evidence"], "model_calls": 1}
        grade = grade_trial(output, [], case["expected"])
        self.assertFalse(grade["checks_passed"])
        self.assertIn("evidence_not_observed_in_tool_results", grade["failures"])
        self.assertIn("required_tool_observation_missing", grade["failures"])

    async def test_partial_investigation_can_finish_without_claiming_resolution(self):
        for case_id in ("conflicting_sources", "persistent_tool_failure"):
            case = next(item for item in self.suite["cases"] if item["case_id"] == case_id)
            tools = ToolSandbox(self.suite["world"], case.get("fixture", {}), user_id="customer-a")
            evidence = []
            order = case["inputs"]["order_id"]
            for name in case["expected"]["required_tools"]:
                args = {"query": "冲突"} if name == "search_knowledge" else {"order_id": order}
                result = await tools.call(name, args)
                evidence.extend(result["evidence_ids"])
            output = {"status": "completed", "answer": "调查已结束，证据仍有冲突或缺失，需要人工核对。",
                      "evidence_ids": evidence, "model_calls": 0}
            grade = grade_trial(output, tools.audit, case["expected"])
            self.assertTrue(grade["checks_passed"], grade)
            self.assertIsNone(grade["task_success"])
            self.assertEqual(grade["status"], "manual_review_required")

    async def test_correct_tool_evidence_still_needs_semantic_review(self):
        async def scripted_adapter(case, tools):
            self.assertEqual(set(case), {"case_id", "task", "inputs", "limits"})
            evidence = []
            for name, args in [
                ("get_order", {"order_id": "A100"}),
                ("get_shipment", {"order_id": "A100"}),
                ("search_knowledge", {"query": "物流延迟"}),
            ]:
                result = await tools.call(name, args)
                evidence.extend(result["evidence_ids"])
            return {"status": "completed", "answer": "这是基础设施固定响应，不证明Agent能力。", "evidence_ids": evidence, "model_calls": 0, "usage": {"prompt_tokens": None, "completion_tokens": None}}

        suite = deepcopy(self.suite)
        suite["cases"] = suite["cases"][:1]
        report = await evaluate_suite(scripted_adapter, suite, suite_sha256=self.digest, repeats=1)
        self.assertEqual(report["summary"]["checks_passed"], 1)
        self.assertEqual(report["trials"][0]["grade"]["status"], "manual_review_required")
        self.assertIsNone(report["summary"]["task_success_rate"])
        self.assertEqual(report["summary"]["usage_unknown_trials"], 1)
        self.assertFalse(report["completion_eligible"])

    async def test_trial_isolation_and_missing_usage_in_live_label(self):
        async def scripted_adapter(case, tools):
            # The first shipment call must fail in every separate trial.
            first = await tools.call("get_shipment", {"order_id": "A100"})
            self.assertEqual(first["error"]["code"], "TOOL_TIMEOUT")
            second = await tools.call("get_shipment", {"order_id": "A100"})
            self.assertEqual(second["status"], "ok")
            return {"status": "completed", "answer": "fixture", "evidence_ids": second["evidence_ids"], "model_calls": 2}

        suite = deepcopy(self.suite)
        case = next(case for case in suite["cases"] if case["case_id"] == "transient_shipment_timeout")
        case["expected"] = {"allowed_statuses": ["completed"], "required_evidence": ["shipment:A100:v1"], "required_error_codes": ["TOOL_TIMEOUT"]}
        suite["cases"] = [case]
        report = await evaluate_suite(scripted_adapter, suite, suite_sha256=self.digest, repeats=3, mode="live")
        self.assertEqual(report["summary"]["checks_passed"], 3)
        self.assertEqual(report["summary"]["usage_unknown_trials"], 3)
        self.assertTrue(all(not trial["model_execution_verified"] for trial in report["trials"]))

    async def test_unimplemented_is_failure_and_evaluation_continues(self):
        async def pending(case, tools):
            raise NotImplementedError("learner")
        report = await evaluate_suite(pending, self.suite, suite_sha256=self.digest, repeats=1)
        self.assertEqual(report["summary"]["checks_passed"], 0)
        self.assertEqual(len(report["trials"]), len(self.suite["cases"]))
        self.assertTrue(all(trial["grade"]["failures"] == ["learner_adapter_not_implemented"] for trial in report["trials"]))

    async def test_deadline_cancels_slow_tool(self):
        async def slow(case, tools):
            await tools.call("get_order", {"order_id": "A100"})
        suite = deepcopy(self.suite)
        case = suite["cases"][0]
        case["fixture"] = {"delays": {"get_order": 1}}
        case["limits"] = {"total_seconds": 0.01}
        suite["cases"] = [case]
        report = await evaluate_suite(slow, suite, suite_sha256=self.digest, repeats=1)
        self.assertEqual(report["trials"][0]["grade"]["failures"], ["trial_deadline_exceeded"])
        self.assertEqual(report["trials"][0]["tool_audit"][0]["result"]["error"]["code"], "TOOL_CANCELLED")
        self.assertEqual(report["summary"]["tool_call_count"], 1)


class CommandTests(unittest.TestCase):
    def test_cli_unimplemented_adapter_returns_nonzero_and_honest_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "report.json"
            # Never depend on learner answers staying unimplemented forever.
            (Path(temporary) / "pending_adapter.py").write_text(
                "async def evaluate_case(case, tools):\n    raise NotImplementedError('fixture only')\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = temporary + os.pathsep + environment.get("PYTHONPATH", "")
            process = subprocess.run(
                [sys.executable, "-X", "utf8", "-m", "scripts.evaluate_agent", "--adapter", "pending_adapter:evaluate_case", "--repeats", "1", "--output", str(target)],
                cwd=PROJECT_ROOT, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
            report = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["checks_passed"], 0)
            self.assertFalse(report["completion_eligible"])


if __name__ == "__main__":
    unittest.main()
