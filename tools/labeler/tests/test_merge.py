import csv

import pytest

from tools.labeler.files import MANIFEST_FIELDS, Layout, write_csv
from tools.labeler.label import LABEL_FIELDS
from tools.labeler.merge import agreement, merge

FILES = [f"crops/s{1 + i // 3}/p_{i}.jpg" for i in range(6)]


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


@pytest.fixture
def layout(tmp_path):
    layout = Layout(tmp_path / "foto_mandiri")
    manifest = [{"file": f, "session": f.split("/")[1], "n": 1} for f in FILES]
    write_csv(layout.manifest, MANIFEST_FIELDS, ({k: r.get(k, "") for k in MANIFEST_FIELDS} for r in manifest))
    return layout


def answers(layout, name, rows):
    write_csv(layout.labels / f"{name}.csv", LABEL_FIELDS, (
        {"file": FILES[i], "part": part, "color": color, "session": FILES[i].split("/")[1]}
        for i, part, color in rows
    ))


def read(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


@pytest.fixture
def labeled(layout):
    answers(layout, "rina", [
        (0, "brick-2x4", "red"),
        (1, "plate-2x4", "white"),       # part disagrees
        (2, "other", "light-gray"),      # color disagrees
        (3, "", "blue"),                 # both doubtful on the part
        (4, "tile-1x2", "black"),        # only rina
    ])
    answers(layout, "budi", [
        (0, "brick-2x4", "red"),
        (1, "brick-2x4", "white"),
        (2, "other", "white"),
        (3, "", "blue"),
    ])
    return layout


def test_label_csv_has_the_agreed_answers_and_empty_disagreements(labeled):
    merge(labeled, "rina", "budi")

    assert read(labeled.label_csv) == [
        {"file": FILES[0], "part": "brick-2x4", "color": "red", "session": "s1"},
        {"file": FILES[1], "part": "", "color": "white", "session": "s1"},
        {"file": FILES[2], "part": "other", "color": "", "session": "s1"},
        {"file": FILES[3], "part": "", "color": "blue", "session": "s2"},
    ]  # crop 4 is left out: only rina answered it
    assert labeled.label_csv.read_text().splitlines()[0] == "file,part,color,session"


def test_the_team_settles_disagreements_in_a_csv(labeled, capsys):
    merge(labeled, "rina", "budi")
    path = labeled.root / "disagreements.csv"
    rows = read(path)
    assert [(r["field"], r["budi"], r["rina"], r["final"]) for r in rows] == [
        ("part", "brick-2x4", "plate-2x4", ""),
        ("color", "white", "light-gray", ""),
    ]

    rows[0]["final"] = "plate-2x4"
    write_csv(path, list(rows[0]), rows)
    merge(labeled, "budi", "rina")  # in either order

    assert read(labeled.label_csv)[1]["part"] == "plate-2x4"
    assert read(labeled.label_csv)[2]["color"] == ""
    assert read(path)[0]["final"] == "plate-2x4"  # kept for the next run
    assert "1 settled, 1 without a final value" in capsys.readouterr().out


def test_a_settled_value_is_dropped_when_a_labeler_changes_their_answer(labeled):
    merge(labeled, "rina", "budi")
    path = labeled.root / "disagreements.csv"
    rows = read(path)
    rows[0]["final"] = "plate-2x4"
    write_csv(path, list(rows[0]), rows)
    answers(labeled, "budi", [(0, "brick-2x4", "red"), (1, "brick-2x2", "white"),
                              (2, "other", "white"), (3, "", "blue")])

    merge(labeled, "rina", "budi")

    assert read(path)[0]["final"] == ""
    assert read(labeled.label_csv)[1]["part"] == ""


def test_unknown_final_values_are_refused(labeled):
    merge(labeled, "rina", "budi")
    path = labeled.root / "disagreements.csv"
    rows = read(path)
    rows[1]["final"] = "purple"
    write_csv(path, list(rows[0]), rows)
    before = labeled.label_csv.read_text()

    with pytest.raises(SystemExit, match="purple"):
        merge(labeled, "rina", "budi")
    assert labeled.label_csv.read_text() == before


def test_disagreements_of_another_pair_are_never_overwritten(labeled):
    merge(labeled, "rina", "budi")
    answers(labeled, "siti", [(0, "brick-2x4", "red")])

    with pytest.raises(SystemExit, match="move it away"):
        merge(labeled, "rina", "siti")


@pytest.mark.parametrize("names", [("rina", "rina"), ("rina", "nobody"), ("../rina", "budi")])
def test_merge_needs_two_labelers_with_answers(labeled, names):
    with pytest.raises(SystemExit):
        merge(labeled, *names)
