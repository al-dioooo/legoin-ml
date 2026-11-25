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


@pytest.mark.parametrize("names", [("rina", "rina"), ("rina", "nobody"), ("../rina", "budi")])
def test_merge_needs_two_labelers_with_answers(labeled, names):
    with pytest.raises(SystemExit):
        merge(labeled, *names)
