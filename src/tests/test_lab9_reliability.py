"""M6 estimators checked against exhaustive sampling without replacement."""
from itertools import combinations

import pytest

from lab9.stats import pass_at_k, pass_hat_k

pytestmark = pytest.mark.student


def test_estimators_match_exhaustive_draws_and_ordering():
    for n in range(1, 8):
        for c in range(n + 1):
            outcomes = [True] * c + [False] * (n - c)
            for k in range(1, n + 1):
                draws = list(combinations(outcomes, k))
                some = sum(any(draw) for draw in draws) / len(draws)
                every = sum(all(draw) for draw in draws) / len(draws)
                assert pass_at_k(n, c, k) == pytest.approx(some)
                assert pass_hat_k(n, c, k) == pytest.approx(every)
                assert pass_hat_k(n, c, k) <= c / n + 1e-12
                assert pass_at_k(n, c, k) >= c / n - 1e-12


@pytest.mark.parametrize("args", [(0, 0, 1), (5, -1, 1), (5, 6, 1), (5, 2, 0),
                                  (5, 2, 6), (5.0, 2, 1), (5, True, 1)])
def test_invalid_reliability_inputs(args):
    for estimator in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError):
            estimator(*args)


def test_one_failure_separates_retry_success_from_reliability():
    assert pass_at_k(5, 4, 5) == 1.0
    assert pass_hat_k(5, 4, 5) == 0.0
