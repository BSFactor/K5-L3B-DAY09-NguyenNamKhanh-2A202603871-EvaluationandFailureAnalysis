"""Reproduce M1 trace evidence without modifying the locked Lab 8 agent.

Run from src/: python -m lab9.m1_evidence
"""
from __future__ import annotations

import json
from pathlib import Path

from lab8.shapes import SHAPES
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

CASES = [
    ("FM-01", "leaky_trace", "C-010", 11, 1),
    ("FM-02", "ignore_denied", "C-007", 11, 4),
    ("FM-03", "ticket_trust", "C-002", 11, 3),
    ("FM-04", "sum_parts", "C-014", 11, 4),
    ("FM-05", "pre_deducted", "C-014", 11, 5),
    ("FM-06", "stale_clause", "C-006", 11, 3),
    ("FM-07", "sibling_refund", "C-011", 11, 4),
    ("FM-08", "misreport", "C-008", 11, 4),
]


def main() -> None:
    cases = []
    for fm, bug, claim, seed, step in CASES:
        shape = f"m1_{bug}"
        SHAPES[shape] = make_shape(shape, {"no_override", bug})
        cases.append({"failure_mode": fm, "shape": shape, "claim_id": claim,
                      "seed": seed, "first_wrong_event": step,
                      "case": investigate(shape, claim, seed),
                      "control": investigate("fixed", claim, seed)})
    baseline = investigate("swarm", "C-002", 55)
    boundary = investigate("fixed", "C-005", 11)
    out = Path("reports/m1_trace_evidence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cases": cases, "swarm_db_override": baseline,
                               "cross_principal_control": boundary},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}: {len(cases)} failure cases with fixed controls")


if __name__ == "__main__":
    main()
