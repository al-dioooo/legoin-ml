"""`merge`: compares two labelers' answers, then writes label.csv for notebooks 02 and 03.

For each field, over the crops both labelers answered, it reports the raw agreement and
Cohen's kappa, with doubtful counted as a value of its own, and lists the disagreements. They
go to `disagreements.csv`, where the team writes the settled value in `final` after looking
at the brick together. Rerunning `merge` reads those values back. A disagreement left without
a `final` stays empty in label.csv, so the notebooks skip that crop for that stage.

Crops that only one labeler answered are left out of label.csv, since nobody checked them.
"""

from collections import Counter
from pathlib import Path

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


def read_settled(path: Path, names: list[str]) -> dict[tuple[str, str, str, str], str]:
    """The team's `final` values, by (file, field, first answer, second answer)."""
    rows = read_csv(path)
    if not rows:
        return {}
    if list(rows[0])[3:5] != names:
        raise SystemExit(
            f"{path.name} compares {list(rows[0])[3:5]}, not {names}; move it away first."
        )
    settled, wrong = {}, []
    for row in rows:
        final = row["final"].strip()
        if final not in FIELDS[row["field"]][1]:
            wrong.append(f"  {row['file']} {row['field']}: {final!r}")
        settled[row["file"], row["field"], row[names[0]], row[names[1]]] = final
    if wrong:
        raise SystemExit(f"Unknown values in {path.name}'s final column:\n" + "\n".join(wrong))
    return settled


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

    path = layout.root / "disagreements.csv"
    settled = read_settled(path, names)
    rows = [
        {"file": f, "session": sessions[f], "field": field, names[0]: x, names[1]: y,
         "final": settled.get((f, field, x, y), "")}
        for f, field, x, y in disagreements
    ]
    write_csv(path, ["file", "session", "field", *names, "final"], rows)
    current = {(f, field, x, y) for f, field, x, y in disagreements}
    if stale := [key for key, value in settled.items() if value and key not in current]:
        print(f"{len(stale)} final values were for answers a labeler has since changed; dropped.")
    decided = {(r["file"], r["field"]): r["final"] for r in rows}
    open_ = sum(not r["final"] for r in rows)
    print(f"\n{len(rows)} disagreements in {layout.rel(path)}: {len(rows) - open_} settled, "
          f"{open_} without a final value (left empty in label.csv).")
    for r in rows:
        if not r["final"]:
            print(f"  {r['file']}  {r['field']}: {names[0]}={shown(r[names[0]])}, "
                  f"{names[1]}={shown(r[names[1]])}")

    final = []
    for f in both:
        row = {"file": f, "session": sessions[f]}
        for field in FIELDS:
            row[field] = a[f][field] if a[f][field] == b[f][field] else decided[f, field]
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
