"""Persist public M6 A/A and flaky-reliability checks, not hidden grading."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

from lab9 import gate
from lab9.eval import load_spec


def main() -> int:
    read = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    spec_path = "config/metric_spec_v2.yaml"
    base_path = "reports/baseline_v2.json"
    flaky_path = "reports/m6_eval_flaky_regression.json"
    spec = load_spec(Path(spec_path))
    base, flaky, aa = read(base_path), read(flaky_path), read("reports/m6_aa.json")
    blocked, _ = gate.check(flaky, base, spec)
    mean_only = deepcopy(spec)
    mean_only.pop("slices", None)
    mean_only["metrics"] = [m for m in spec["metrics"] if m["id"] == "pass_rate"]
    mean_blocked, mean_lines = gate.check(flaky, base, mean_only)
    floor_only = deepcopy(mean_only)
    floor_only["metrics"][0]["threshold"].pop("no_significant_drop", None)
    floor_blocked, _ = gate.check(flaky, base, floor_only)
    process = subprocess.run([sys.executable, "-m", "lab9.gate", "--pr", flaky_path,
                              "--baseline", base_path, "--spec", spec_path],
                             capture_output=True, text=True)
    floor = next(m["threshold"]["min"] for m in spec["metrics"] if m["id"] == "pass_hat_5")
    aa_rates = [aa[name]["metrics"]["pass_hat_5"] for name in ("first", "second")]
    margin = min(aa_rates) - floor
    passed = (all(delta == 0 for delta in aa["deltas"].values()) and margin > 0
              and process.returncode == 1 and "pass_hat_5" in blocked and not floor_blocked)
    out = Path("reports/m6_verification.json")
    out.write_text(json.dumps({"scope": "public M6 checks only", "passed": passed,
                               "aa_pass_hat_5": aa_rates, "floor": floor, "margin": margin,
                               "flaky_metrics": flaky["metrics"], "blocked": blocked,
                               "mean_pass_rate_only_blocked": mean_blocked,
                               "mean_pass_rate_only_lines": mean_lines,
                               "mean_pass_rate_floor_only_blocked": floor_blocked,
                               "note": "The full mean-rate CI also detects this public variant; only its absolute floor passes.",
                               "gate_exit": process.returncode, "stdout": process.stdout,
                               "stderr": process.stderr}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(process.stdout, end="")
    print("\n".join(mean_lines))
    print(f"M6 public checks {'PASS' if passed else 'FAIL'}; wrote {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
