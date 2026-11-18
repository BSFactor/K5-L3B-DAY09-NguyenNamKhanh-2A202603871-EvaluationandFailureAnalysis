"""M5: slice checks use paired item means and honor generic slice rules."""
import copy

import pytest

from lab9.gate import slice_check

pytestmark = pytest.mark.student


def report(values):
    return {"rows": [{"item_id": item, "seed": seed, "score": value,
                      "slices": ["target"]}
                     for item, samples in values.items()
                     for seed, value in enumerate(samples)]}


def spec(**overrides):
    return {"slices": [{"name": "target", "metric": "score", "min": 0.8,
                        "blocking": True, **overrides}],
            "bootstrap": {"rng": 2027, "n_resamples": 1000, "confidence": 0.95}}


def test_slice_floor_includes_equality_and_averages_per_item():
    # Item means .6 and 1.0 => .8, despite different numbers of rows per item.
    pr = report({"a": [0.6], "b": [1.0, 1.0, 1.0]})
    blocked, _ = slice_check(pr, pr, spec())
    assert blocked == []


def test_paired_drop_blocks_even_above_floor_with_shuffled_rows():
    base = report({"a": [1, 1], "b": [1, 1], "c": [1, 1]})
    pr = report({"c": [0.9, 0.9], "b": [0.9, 0.9], "a": [0.9, 0.9]})
    blocked, lines = slice_check(pr, base, spec(no_significant_drop=True))
    assert blocked == ["slice:target/score"]
    assert "CI [-0.100, -0.100]" in lines[0]


def test_nonblocking_slice_warns_without_blocking():
    base = report({"a": [1], "b": [1]})
    pr = report({"a": [0], "b": [0]})
    blocked, lines = slice_check(pr, base, spec(blocking=False))
    assert blocked == []
    assert "warn" in lines[0]


def test_identical_slice_has_zero_ci():
    base = report({"a": [1, 1], "b": [1, 1]})
    blocked, lines = slice_check(copy.deepcopy(base), base, spec(no_significant_drop=True))
    assert blocked == []
    assert "CI [+0.000, +0.000]" in lines[0]


@pytest.mark.parametrize("values", [{}, {"a": [1]}, {"a": [1], "other": [1]}])
def test_missing_or_unpaired_slice_cannot_silently_pass(values):
    base = report({"a": [1], "b": [1]})
    blocked, lines = slice_check(report(values), base, spec(no_significant_drop=True))
    assert blocked == ["slice:target/score"]
    assert "unpaired" in lines[0]
