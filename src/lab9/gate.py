"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from numbers import Real
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = [m["id"] for m in spec["metrics"]
              if m["id"] not in ("pass_5", "cost_per_success")
              and not m["id"].startswith(("pass_at_", "pass_hat_"))]
    pairs, slices = {}, {}
    for name, report in (("PR", pr), ("baseline", base)):
        errors, keys, tags = _report_integrity(report, spec, graded)
        problems.extend(f"{name}: {e}" for e in errors)
        pairs[name], slices[name] = keys, tags
    if pairs["PR"] != pairs["baseline"]:
        problems.append("PR (item_id, seed) set differs from baseline")
    if slices["PR"] != slices["baseline"]:
        problems.append("PR item slice tags differ from baseline")
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        for section, identity in (("metrics", lambda r: r["id"]),
                                  ("slices", lambda r: (r["name"], r["metric"]))):
            current = {identity(r): r for r in spec.get(section, [])}
            if len(current) != len(spec.get(section, [])):
                problems.append(f"RATCHET duplicate {section} rules")
            for old in base_spec.get(section, []):
                key = identity(old)
                new = current.get(key)
                if new is None:
                    problems.append(f"RATCHET removed {section} rule {key}")
                    continue
                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"RATCHET disabled blocking for {key}")
                for field in ("kind", "level", "grader"):
                    if field in old and new.get(field) != old[field]:
                        problems.append(f"RATCHET changed {field} for {key}")
                old_th = old.get("threshold", {}) if section == "metrics" else old
                new_th = (new.get("threshold") or {}) if section == "metrics" else new
                if not isinstance(new_th, dict):
                    problems.append(f"RATCHET invalid threshold for {key}")
                    continue
                for bound in ("min", "max", "max_increase"):
                    if bound not in old_th:
                        continue
                    value = new_th.get(bound)
                    if not _finite(value) or (value < old_th[bound] if bound == "min" else value > old_th[bound]):
                        problems.append(f"RATCHET loosened {bound} for {key}")
                if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
                    problems.append(f"RATCHET removed no_significant_drop for {key}")
    return problems


def _finite(value) -> bool:
    try:
        return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _report_integrity(report: dict, spec: dict, graded: list[str]) -> tuple[list[str], set, dict]:
    errors, keys, slices = [], set(), {}
    if not isinstance(report, dict):
        return ["report must be an object"], keys, slices
    manifest, rows, metrics = report.get("manifest"), report.get("rows"), report.get("metrics")
    if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
        return ["invalid manifest/rows/metrics structure"], keys, slices
    if report.get("evaluator_failures") != []:
        errors.append("evaluator_failures missing, malformed or nonempty")
    seeds, count = manifest.get("seeds"), manifest.get("items")
    if (not isinstance(seeds, list) or not seeds
            or any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds)
            or type(count) is not int or count < 1):
        return [*errors, "invalid item count or duplicate/invalid seeds"], keys, slices
    if len(rows) != count * len(seeds):
        errors.append("row count differs from manifest items x seeds")
    for metric, value in metrics.items():
        if not _finite(value):
            errors.append(f"metric {metric} is missing/nonfinite/nonnumeric")
    for rule in spec["metrics"]:
        if not _finite(metrics.get(rule["id"])):
            errors.append(f"required metric {rule['id']} missing or invalid")
        th = rule.get("threshold", {})
        if not isinstance(th, dict):
            errors.append(f"invalid threshold structure for {rule['id']}")
            continue
        for bound in ("min", "max", "max_increase"):
            if bound in th and not _finite(th[bound]):
                errors.append(f"invalid threshold {rule['id']}/{bound}")
    for index, row in enumerate(rows):
        if (not isinstance(row, dict) or not isinstance(row.get("item_id"), str)
                or not row.get("item_id") or type(row.get("seed")) is not int):
            errors.append(f"invalid row identity at index {index}")
            continue
        key = (row["item_id"], row["seed"])
        if key in keys:
            errors.append(f"duplicate (item_id, seed): {key}")
        keys.add(key)
        tags = row.get("slices", [])
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            errors.append(f"invalid slice tags for {key}")
        else:
            tags = frozenset(tags)
            if row["item_id"] in slices and slices[row["item_id"]] != tags:
                errors.append(f"inconsistent slice tags across seeds for {row['item_id']}")
            slices[row["item_id"]] = tags
        for metric in graded:
            value = row.get(metric)
            if not (isinstance(value, bool) or (_finite(value) and 0 <= value <= 1)):
                errors.append(f"row {key}: {metric} missing/nonfinite/invalid")
        if "cost" in row and (not _finite(row["cost"]) or row["cost"] < 0):
            errors.append(f"row {key}: invalid cost")
        if "cost_per_success" in metrics and "cost" not in row:
            errors.append(f"row {key}: cost missing")
    items = {item for item, _ in keys}
    if len(items) != count or keys != {(item, seed) for item in items for seed in seeds}:
        errors.append("rows do not cover the complete item x seed grid")
    # Check aggregates against row evidence, including reliability and cost.
    # Do not recompute a broken report: missing values must never be dropped.
    if not errors:
        normalized = [{**row, "cost": row.get("cost", 0.0)} for row in rows]
        recomputed = aggregate(normalized, graded, k_values=spec.get("pass_k", []))
        for metric, value in metrics.items():
            if metric in recomputed and (not _finite(recomputed[metric])
                                         or not math.isclose(value, recomputed[metric], rel_tol=0, abs_tol=1e-9)):
                errors.append(f"aggregate {metric} differs from rows")
    return errors, keys, slices


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        sid = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        value = sum(a.values()) / len(a) if a else None
        failed = False
        notes = []
        if not a or not b or set(a) != set(b):
            failed = True
            notes.append("missing or unpaired slice items")
        else:
            if "min" in rule and value < rule["min"]:
                failed = True
                notes.append(f"below floor {rule['min']}")
            if rule.get("no_significant_drop"):
                keys = sorted(a)
                try:
                    d, lo, hi = stats.paired_bootstrap(
                        [a[k] for k in keys], [b[k] for k in keys],
                        n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                        confidence=bs.get("confidence", 0.95))
                except ValueError as exc:
                    failed = True
                    notes.append(f"cannot estimate paired CI: {exc}")
                else:
                    notes.append(f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]")
                    if hi < 0:
                        failed = True
        blocking = bool(rule.get("blocking"))
        if failed and blocking:
            blocked.append(sid)
        verdict = ("BLOCK" if blocking else "warn") if failed else "ok"
        lines.append(f"  {sid:<36} {str(value):<8} items={len(a)} {'; '.join(notes)} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    if not pr["manifest"].get("eval_set_sha") or pr["manifest"]["eval_set_sha"] != base["manifest"].get("eval_set_sha"):
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr.get('run_id', '?') if isinstance(pr, dict) else '?'} "
          f"vs main {base.get('run_id', '?') if isinstance(base, dict) else '?'}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
