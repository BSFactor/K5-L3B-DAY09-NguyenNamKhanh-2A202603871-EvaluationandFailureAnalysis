"""Run the generated traps through the gate CLI and persist explicit verdicts."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def main() -> int:
    results = []
    for path in sorted(Path("reports/traps").glob("*.json")):
        altered_spec = path.with_suffix(".spec.yaml")
        command = [sys.executable, "-m", "lab9.gate", "--pr", str(path),
                   "--baseline", "reports/baseline_v2.json", "--spec",
                   str(altered_spec) if altered_spec.is_file() else "config/metric_spec_v2.yaml"]
        if altered_spec.is_file():
            command += ["--base-spec", "config/metric_spec_v2.yaml"]
        process = subprocess.run(command, capture_output=True, text=True)
        passed = (process.returncode == 1 and "INTEGRITY" in process.stdout
                  and "exit 1 — blocked: integrity" in process.stdout
                  and (not altered_spec.is_file() or "RATCHET" in process.stdout))
        results.append({"trap": path.stem, "exit_code": process.returncode, "passed": passed,
                        "stdout": process.stdout, "stderr": process.stderr})
        print(f"{path.stem}: " + next((line for line in process.stdout.splitlines()
                                             if line.startswith("exit ")), "missing explicit verdict"))
    mutation = json.loads(Path("reports/m7_mutation.json").read_text(encoding="utf-8"))
    passed = (len(results) >= 4 and all(r["passed"] for r in results)
              and mutation["regressions_blocked"] == mutation["regressions"]
              and mutation["false_alarms"] == 0)
    out = Path("reports/m7_verification.json")
    out.write_text(json.dumps({"scope": "supplied traps and variants; hidden grader not run",
                               "passed": passed, "traps": results, "mutation": mutation},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"M7 supplied checks {'PASS' if passed else 'FAIL'}; wrote {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
