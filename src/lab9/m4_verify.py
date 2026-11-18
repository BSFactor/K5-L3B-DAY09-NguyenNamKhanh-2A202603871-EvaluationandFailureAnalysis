"""Verify the M4 command-line gates against freshly generated reports.

Run after the four eval commands: python -m lab9.m4_verify
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from lab9 import ci_check, gate, stats
from lab9.eval import load_spec, per_item


def main() -> int:
    spec = load_spec()
    baseline = Path("reports/baseline_v1.json")
    base = json.loads(baseline.read_text(encoding="utf-8"))
    results = []
    for path, expected in [("reports/eval_pr.json", 0), ("reports/eval_fixed.json", 0),
                           ("reports/eval_seeded_regression.json", 1)]:
        pr = json.loads(Path(path).read_text(encoding="utf-8"))
        command = [sys.executable, "-m", "lab9.gate", "--pr", path, "--baseline", str(baseline)]
        process = subprocess.run(command, capture_output=True, text=True)
        blocked, _ = gate.check(pr, base, spec)
        a, b = per_item(pr, "pass_rate"), per_item(base, "pass_rate")
        keys = sorted(a)
        delta, low, high = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                                n_resamples=spec["bootstrap"]["n_resamples"],
                                                rng=spec["bootstrap"]["rng"],
                                                confidence=spec["bootstrap"]["confidence"])
        results.append({"report": path, "run_id": pr["run_id"], "expected_exit": expected,
                        "actual_exit": process.returncode, "blocked": blocked,
                        "pass_rate_delta": delta, "pass_rate_ci": [low, high],
                        "stdout": process.stdout, "stderr": process.stderr})
        print(process.stdout, end="")
    current = json.loads(Path("reports/eval_pr.json").read_text(encoding="utf-8"))
    problems = ci_check.check(current, base, spec)
    regression = results[-1]
    passed = (not problems and all(r["actual_exit"] == r["expected_exit"] for r in results)
              and "pass_rate" in regression["blocked"]
              and abs(regression["pass_rate_delta"] + 0.271) <= 0.01
              and abs(regression["pass_rate_ci"][0] + 0.500) <= 0.01
              and abs(regression["pass_rate_ci"][1] + 0.057) <= 0.01)
    out = Path("reports/m4_verification.json")
    out.write_text(json.dumps({"passed": passed, "baseline_run_id": base["run_id"],
                               "ci_check_problems": problems, "gates": results},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"M4 {'PASS' if passed else 'FAIL'}; wrote {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
