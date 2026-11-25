"""`merge`: compares two labelers' answers, then writes label.csv for notebooks 02 and 03."""

from collections import Counter


def agreement(pairs: list[tuple[str, str]]) -> tuple[float, float | None]:
    """Raw agreement and Cohen's kappa; kappa is None when both always gave one same value."""
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(first[value] * second[value] for value in first) / n**2
    return observed, None if expected == 1 else (observed - expected) / (1 - expected)
