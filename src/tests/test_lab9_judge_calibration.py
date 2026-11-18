"""M2 calibration edge cases and the deliberately unsuitable helpfulness judge."""
import csv
import math
from pathlib import Path

import pytest

from lab9 import stats
from lab9.judge import calibrate

pytestmark = pytest.mark.student


def test_helpful_rejected_despite_perfect_precision():
    result = calibrate(Path("data/eval/judge_helpful_public.csv"))
    assert result["confusion"] == {"tp": 9, "fp": 0, "fn": 21, "tn": 70}
    assert result["precision"] == 1.0
    assert result["recall"] == 0.3
    assert result["kappa"] == 0.375
    assert result["passed"] is False


def test_constant_judge_fails_without_crashing_correction(tmp_path):
    path = tmp_path / "constant.csv"
    path.write_text("item_id,reply,human,judge\nX,ok,PASS,PASS\n", encoding="utf-8")
    result = calibrate(path)
    assert math.isnan(result["kappa"])
    assert result["corrected_fail_rate"] is None
    assert result["passed"] is False


def test_floor_uses_unrounded_statistics(tmp_path):
    # Precision 1600/2001 = 0.7996 displays as 0.800 but is below the floor.
    path = tmp_path / "boundary.csv"
    with path.open("w", newline="", encoding="utf-8") as source:
        writer = csv.writer(source)
        writer.writerow(["item_id", "reply", "human", "judge"])
        for h, j, count in [("FAIL", "FAIL", 1600), ("PASS", "FAIL", 401),
                            ("PASS", "PASS", 8000)]:
            writer.writerows((f"{h}-{j}-{i}", "text", h, j) for i in range(count))
    result = calibrate(path)
    assert result["precision"] == 0.8
    assert result["kappa"] > 0.6 and result["recall"] == 1.0
    assert result["passed"] is False


@pytest.mark.parametrize("human,judge", [(["FAIL"], []), (["UNKNOWN"], ["PASS"])])
def test_confusion_rejects_invalid_labels(human, judge):
    with pytest.raises(ValueError):
        stats.confusion(human, judge)


def test_empty_metrics_and_zero_denominators():
    assert stats.precision_recall([], []) == (0.0, 0.0)
    assert stats.precision_recall(["PASS"], ["PASS"]) == (0.0, 0.0)
    with pytest.raises(ValueError):
        stats.cohen_kappa([], [])


@pytest.mark.parametrize("rates", [(0.2, 0.5, 0.5), (0.2, 0.2, 0.3),
                                   (float("nan"), 0.8, 0.9), (1.1, 0.8, 0.9)])
def test_correction_rejects_uninformative_or_invalid_rates(rates):
    with pytest.raises(ValueError):
        stats.rogan_gladen(*rates)


def test_correction_upper_clip():
    assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0
