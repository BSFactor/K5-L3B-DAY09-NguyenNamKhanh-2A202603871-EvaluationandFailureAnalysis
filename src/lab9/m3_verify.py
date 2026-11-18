"""Measure M3 grader detection on supplied bugs and false alarms on fixed.

Run from src/: python -m lab9.m3_verify. The cases name mechanisms, not gate rules.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic_evals.evaluators import EvaluatorContext

from lab8.shapes import SHAPES
from lab9.graders import GRADERS
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

# Claim chosen to actually trigger the mechanism; run all five fixed seeds.
CASES = [
    ("leaky_trace", "C-010", "secret_leak"),
    ("ignore_denied", "C-007", "pass_rate"),
    ("ticket_trust", "C-002", "db_fact_kept"),
    ("sum_parts", "C-014", "refund_amount_correct"),
    ("round_down", "C-001", "refund_amount_correct"),
    ("pre_deducted", "C-014", "refund_amount_correct"),
    ("stale_clause", "C-006", "refund_amount_correct"),
    ("sibling_refund", "C-011", "approval_bypass"),
    ("misreport", "C-008", "reply_amount_correct"),
]
SEEDS = [11, 22, 33, 44, 55]


def scores(case: dict) -> dict[str, bool]:
    ctx = EvaluatorContext(name="m3", inputs={}, metadata=None,
                           expected_output=case["label"], output=case["trial"],
                           duration=0.0, _span_tree=None, attributes={}, metrics={})
    return {name: bool(grader().evaluate(ctx).value) for name, grader in GRADERS.items()}


def is_bad(metric: str, value: bool) -> bool:
    return value if metric in ("approval_bypass", "secret_leak") else not value


def main() -> int:
    rows = []
    for bug, claim, metric in CASES:
        shape = f"m3_{bug}"
        SHAPES[shape] = make_shape(shape, {"no_override", bug})
        for seed in SEEDS:
            case = investigate(shape, claim, seed)
            result = scores(case)
            rows.append({"bug": bug, "claim_id": claim, "seed": seed,
                         "target_metric": metric, "scores": result,
                         "detected": is_bad(metric, result[metric])})
    claims = [json.loads(line)["claim_id"] for line in Path("data/public_claims.jsonl").read_text().splitlines()]
    controls = []
    for claim in claims:
        for seed in SEEDS:
            result = scores(investigate("fixed", claim, seed))
            controls.append({"claim_id": claim, "seed": seed, "scores": result,
                             "false_alarm": any(is_bad(m, v) for m, v in result.items())})
    detection = sum(row["detected"] for row in rows) / len(rows)
    fpr = sum(row["false_alarm"] for row in controls) / len(controls)
    report = {"seeds": SEEDS, "faulty_trials": len(rows), "fixed_trials": len(controls),
              "detection_rate": detection, "false_positive_rate": fpr,
              "passed": detection >= 0.8 and fpr <= 0.1,
              "faulty_rows": rows, "fixed_rows": controls}
    out = Path("reports/m3_verification.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"detection={detection:.1%} ({len(rows)} faulty trials); false alarms={fpr:.1%} ({len(controls)} fixed trials)")
    print(f"wrote {out}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
