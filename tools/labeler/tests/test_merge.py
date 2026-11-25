import pytest

from tools.labeler.merge import agreement


def test_kappa_matches_the_textbook_example():
    # 50 items: both yes 20, A yes/B no 5, A no/B yes 10, both no 15.
    pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15

    observed, kappa = agreement(pairs)

    assert observed == pytest.approx(0.7)
    assert kappa == pytest.approx(0.4)  # p_e = 0.6 × 0.5 + 0.4 × 0.5 = 0.5


def test_kappa_is_undefined_when_both_always_gave_one_value():
    assert agreement([("red", "red")] * 4) == (1.0, None)


def test_kappa_counts_doubtful_as_its_own_value():
    observed, kappa = agreement([("red", "red"), ("", ""), ("red", ""), ("", "red")])

    assert (observed, kappa) == (0.5, pytest.approx(0.0))
