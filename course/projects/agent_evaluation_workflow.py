"""Day20 learner workspace: evaluate an Agent, never substitute fixture pass for mastery.

The supplied evaluator records actual tool activity. This module is where you
design a baseline/candidate comparison and join semantic review to those trials.
Do not copy an author report or treat --mode live as proof of provider execution.
"""
from typing import Any


def prepare_experiment(cases: list[dict[str, Any]], split_policy: dict) -> dict:
    """Return grouped development/validation/test IDs and leakage diagnostics.

    Freeze task intent, scenario-family IDs, suite hash, model/prompt/tool-schema
    versions, repeat count, budgets and acceptance thresholds before comparison.
    Public classroom cases remain practice data even when named test locally.
    """
    raise NotImplementedError("Define and freeze your Agent evaluation protocol")


def compare_trials(baseline: dict, candidate: dict, reviews: list[dict]) -> dict:
    """Join by case_id/repeat; retain failures, missing usage and review uncertainty.

    Output per-task differences, critical violations, reviewed task success and
    review coverage, tool-evidence checks, recovery outcomes, latency and usage.
    A missing review must not count as a semantic pass. Do not select a candidate
    on the reserved test set or infer provider cost from a missing token count.
    """
    raise NotImplementedError("Compare observed trials with explicit review evidence")
