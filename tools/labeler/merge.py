"""`merge`: compares two labelers' answers, then writes label.csv for notebooks 02 and 03.

For each field, over the crops both labelers answered, it reports the raw agreement and
Cohen's kappa, with doubtful counted as a value of its own, and lists the disagreements. A
disagreement stays empty in label.csv, so the notebooks skip that crop for that stage.

Crops that only one labeler answered are left out of label.csv, since nobody checked them.
"""

from collections import Counter

from .catalogue import (
    COLOR_VALUES,
    COLORS,
    DOUBTFUL,
    OTHER,
    PART_VALUES,
    PARTS,
    TARGET,
    TARGET_OTHER,
)
from .files import Layout, read_csv, write_csv
from .label import LABEL_FIELDS, NAME

FIELDS = {"part": (PARTS, PART_VALUES), "color": (COLORS, COLOR_VALUES)}


def agreement(pairs: list[tuple[str, str]]) -> tuple[float, float | None]:
    """Raw agreement and Cohen's kappa; kappa is None when both always gave one same value."""
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(first[value] * second[value] for value in first) / n**2
    return observed, None if expected == 1 else (observed - expected) / (1 - expected)


def shown(value: str) -> str:
    return "(doubtful)" if value == DOUBTFUL else value


def read_labels(layout: Layout, name: str) -> dict[str, dict[str, str]]:
    path = layout.labels / f"{name}.csv"
    if not NAME.match(name) or not path.exists():
        raise SystemExit(f"No answers from {name!r}: {path} doesn't exist.")
    return {row["file"]: row for row in read_csv(path)}


def merge(layout: Layout, first: str, second: str) -> None:
    names = sorted({first, second})
    if len(names) != 2:
        raise SystemExit("merge compares two different labelers.")
    a, b = (read_labels(layout, name) for name in names)
    sessions = {row["file"]: row["session"] for row in read_csv(layout.manifest)}
    both = [f for f in sessions if f in a and f in b]  # in the manifest's order
    gone = sorted((set(a) | set(b)) - set(sessions))
    print(f"{names[0]} vs {names[1]}: {len(both)} crops answered by both.")
    for name, mine, theirs in ((names[0], a, b), (names[1], b, a)):
        if only := [f for f in sessions if f in mine and f not in theirs]:
            print(f"  {len(only)} answered only by {name}, left out until both have.")
    if gone:
        print(f"  {len(gone)} answers for crops no longer in the manifest, ignored.")
    if not both:
        raise SystemExit("Nothing to merge yet.")

    disagreements = []
    for field in FIELDS:
        pairs = [(a[f][field], b[f][field]) for f in both]
        observed, kappa = agreement(pairs)
        same = sum(x == y for x, y in pairs)
        kappa_text = "n/a (one value only)" if kappa is None else f"{kappa:.3f}"
        print(f"{field:>5}: agreement {observed:.1%} ({same}/{len(pairs)}), Cohen's kappa {kappa_text}")
        mixed = Counter(tuple(sorted(map(shown, pair))) for pair in pairs if pair[0] != pair[1])
        if mixed:
            print("       most often mixed up: " + ", ".join(
                f"{x}/{y} ({k})" for (x, y), k in mixed.most_common(5)))
        disagreements += [(f, field, a[f][field], b[f][field]) for f in both if a[f][field] != b[f][field]]

    print(f"\n{len(disagreements)} disagreements, left empty in label.csv:")
    for f, field, x, y in disagreements:
        print(f"  {f}  {field}: {names[0]}={shown(x)}, {names[1]}={shown(y)}")

    final = []
    for f in both:
        row = {"file": f, "session": sessions[f]}
        for field in FIELDS:
            row[field] = a[f][field] if a[f][field] == b[f][field] else DOUBTFUL
        final.append(row)
    write_csv(layout.label_csv, LABEL_FIELDS, final)
    print(f"\nWrote {layout.rel(layout.label_csv)}: {len(final)} crops.")
    for field, (catalogue, _) in FIELDS.items():
        counts = Counter(row[field] for row in final)
        short = [f"{c} {counts[c]}/{TARGET}" for c in catalogue if counts[c] < TARGET]
        if counts[OTHER] < TARGET_OTHER:
            short.append(f"{OTHER} {counts[OTHER]}/{TARGET_OTHER}")
        print(f"{field:>5}: {sum(counts.values()) - counts[DOUBTFUL]} labeled, "
              f"{counts[DOUBTFUL]} doubtful. Below target: {', '.join(short) or 'none'}")
