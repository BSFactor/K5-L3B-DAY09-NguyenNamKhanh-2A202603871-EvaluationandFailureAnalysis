"""M7: corrupt healthy reports, including cases with no metric-floor failure."""
from copy import deepcopy

import pytest

from lab9 import gate
from lab9.eval import aggregate

pytestmark = pytest.mark.student


@pytest.fixture
def clean():
    rows = [{"item_id": f"E-{i}", "seed": s, "pass_rate": True,
             "approval_bypass": False, "cost": 1.0, "slices": ["target"]}
            for i in range(4) for s in (11, 22)]
    spec = {"eval_set_version": "v2", "pass_k": [1, 2], "metrics": [
        {"id": "pass_rate", "kind": "capability", "blocking": True,
         "threshold": {"min": 0.8, "no_significant_drop": True}},
        {"id": "approval_bypass", "kind": "safety", "blocking": True, "threshold": {"max": 0}},
        {"id": "cost_per_success", "kind": "system", "blocking": False,
         "threshold": {"max_increase": 0.1}},
        {"id": "pass_hat_2", "kind": "capability", "blocking": True, "threshold": {"min": 0.8}}],
        "slices": [{"name": "target", "metric": "pass_rate", "min": 0.9,
                    "no_significant_drop": True, "blocking": True}]}
    report = {"manifest": {"eval_set_sha": "x", "items": 4, "seeds": [11, 22]},
              "rows": rows, "metrics": aggregate(rows, ["pass_rate", "approval_bypass"], [1, 2]),
              "evaluator_failures": []}
    return report, spec


def test_clean_report_and_stricter_spec_pass_integrity(clean):
    report, spec = clean
    strict = deepcopy(spec)
    strict["metrics"][0]["threshold"]["min"] = 0.9
    assert gate.integrity_check(report, report, strict, spec) == []
    assert gate.check(report, report, spec, spec)[0] == []


@pytest.mark.parametrize("damage", [
    lambda r: r["rows"].__setitem__(0, deepcopy(r["rows"][1])),
    lambda r: r["rows"].pop(),
    lambda r: r["manifest"].__setitem__("seeds", [11, 11]),
    lambda r: r["rows"][0].__setitem__("pass_rate", None),
    lambda r: r["rows"][0].__setitem__("pass_rate", float("nan")),
    lambda r: r["rows"][0].__setitem__("pass_rate", "PASS"),
    lambda r: r["rows"][0].__setitem__("cost", float("inf")),
    lambda r: r["rows"][0].__setitem__("cost", -1),
    lambda r: r["rows"][0].__setitem__("slices", []),
    lambda r: [row.__setitem__("slices", []) for row in r["rows"]],
    lambda r: r["evaluator_failures"].append("grader crashed on an otherwise green run"),
    lambda r: r["metrics"].__setitem__("pass_rate", float("nan")),
    lambda r: r["metrics"].pop("pass_hat_2"),
    lambda r: r["metrics"].__setitem__("cost_per_success", 0.0),
    lambda r: r["metrics"].__setitem__("pass_hat_2", 0.5),
])
def test_corrupt_green_report_blocked_as_integrity(clean, damage):
    base, spec = clean
    corrupt = deepcopy(base)
    damage(corrupt)
    blocked, lines = gate.check(corrupt, base, spec)
    assert blocked == ["integrity"]
    assert any("INTEGRITY" in line for line in lines)


@pytest.mark.parametrize("weaken", [
    lambda s: s["metrics"][0]["threshold"].__setitem__("min", 0.7),
    lambda s: s["metrics"][0]["threshold"].pop("min"),
    lambda s: s["metrics"][0].__setitem__("threshold", None),
    lambda s: s["metrics"][0]["threshold"].pop("no_significant_drop"),
    lambda s: s["metrics"][0].__setitem__("blocking", False),
    lambda s: s["metrics"].pop(0),
    lambda s: s["metrics"][1]["threshold"].__setitem__("max", 1),
    lambda s: s["metrics"][2]["threshold"].__setitem__("max_increase", 0.5),
    lambda s: s.__setitem__("slices", []),
    lambda s: s["slices"][0].__setitem__("metric", "another_metric"),
    lambda s: s["slices"][0].__setitem__("min", 0.5),
    lambda s: s["slices"][0].pop("no_significant_drop"),
    lambda s: s["slices"][0].__setitem__("blocking", False),
])
def test_ratchet_rejects_weaker_rules_on_green_report(clean, weaken):
    report, spec = clean
    loose = deepcopy(spec)
    weaken(loose)
    errors = gate.integrity_check(report, report, loose, spec)
    assert any("RATCHET" in error for error in errors)


def test_corrupt_baseline_is_also_rejected(clean):
    report, spec = clean
    base = deepcopy(report)
    base["evaluator_failures"] = ["error"]
    assert any("baseline" in error for error in gate.integrity_check(report, base, spec))
