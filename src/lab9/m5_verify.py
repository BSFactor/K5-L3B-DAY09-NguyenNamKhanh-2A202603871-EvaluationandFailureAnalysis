"""Verify public M5 slice behavior; this does not run the private instructor grader."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

from lab9 import evalset, gate, stats
from lab9.eval import load_spec, per_item


def main() -> int:
    spec_path = Path("config/metric_spec_v2.yaml")
    spec = load_spec(spec_path)
    baseline_path = Path("reports/baseline_v2.json")
    base = json.loads(baseline_path.read_text(encoding="utf-8"))
    unsliced = deepcopy(spec)
    unsliced.pop("slices", None)
    results = []
    for shape in ("slice_regression", "fixed", "honest_refactor"):
        path = Path(f"reports/m5_eval_{shape}.json")
        pr = json.loads(path.read_text(encoding="utf-8"))
        command = [sys.executable, "-m", "lab9.gate", "--pr", str(path),
                   "--baseline", str(baseline_path), "--spec", str(spec_path)]
        process = subprocess.run(command, capture_output=True, text=True)
        blocked, _ = gate.check(pr, base, spec)
        global_blocked, _ = gate.check(pr, base, unsliced)
        slices = {}
        for rule in spec["slices"]:
            a = per_item(pr, rule["metric"], rule["name"])
            b = per_item(base, rule["metric"], rule["name"])
            keys = sorted(a)
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                              **{k: spec["bootstrap"][k]
                                                 for k in ("rng", "confidence", "n_resamples")})
            slices[rule["name"]] = {"items": len(a), "value": sum(a.values()) / len(a),
                                     "delta": d, "ci": [lo, hi]}
        results.append({"shape": shape, "run_id": pr["run_id"], "exit_code": process.returncode,
                        "blocked": blocked, "global_only_blocked": global_blocked,
                        "slices": slices, "stdout": process.stdout, "stderr": process.stderr})
        print(process.stdout, end="")
    items = evalset.load_jsonl(evalset.ITEMS_V2)
    coverage = Counter(fm for item in items for fm in set(item["failure_modes"]))
    problems = evalset.check(evalset.ITEMS_V2, evalset.LABELS_V2)
    regression, *controls = results
    passed = (not problems and regression["exit_code"] == 1
              and regression["blocked"] == ["slice:money_movement/pass_rate"]
              and not regression["global_only_blocked"]
              and all(c["exit_code"] == 0 and not c["blocked"] for c in controls))
    out = Path("reports/m5_verification.json")
    out.write_text(json.dumps({"passed": passed, "scope": "public M5 checks only",
                               "eval_set_sha": evalset.sha12(evalset.ITEMS_V2),
                               "coverage": dict(sorted(coverage.items())),
                               "evalset_problems": problems, "gates": results},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"M5 public checks {'PASS' if passed else 'FAIL'}; wrote {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
