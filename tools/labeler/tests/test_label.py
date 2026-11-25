import csv

import pytest

from tools.labeler.files import MANIFEST_FIELDS, Layout, write_csv
from tools.labeler.label import LabelError, Labels


def crop(session, photo, n):
    return {
        "file": f"crops/{session}/{photo}_{n}.jpg", "session": session,
        "photo": f"photos/{session}/{photo}.jpg", "preview": f"preview/{session}/{photo}.jpg",
        "width": 640, "height": 480, "n": n, "score": 0.9, "x1": 10, "y1": 10, "x2": 50,
        "y2": 50, "crop_x1": 5, "crop_y1": 5, "crop_x2": 55, "crop_y2": 55,
    }


@pytest.fixture
def layout(tmp_path):
    layout = Layout(tmp_path / "foto_mandiri")
    crops = [crop("s1", "a", 1), crop("s1", "a", 2), crop("s2", "b", 1)]
    write_csv(layout.manifest, MANIFEST_FIELDS, crops)
    for row in crops:
        (layout.root / row["file"]).parent.mkdir(parents=True, exist_ok=True)
        (layout.root / row["file"]).write_bytes(b"\xff\xd8 not really a jpeg")
    return layout


def rows(path):
    with path.open(newline="") as file:
        return list(csv.reader(file))


def test_answers_are_written_in_label_csv_format_after_each_crop(layout):
    labels = Labels(layout)

    labels.save("rina", "crops/s2/b_1.jpg", "other", "")
    labels.save("rina", "crops/s1/a_1.jpg", "brick-2x4", "light-gray")

    # Notebooks 02 and 03 read `file,part,color`, relative to the CSV's folder; empty = doubtful.
    assert rows(layout.labels / "rina.csv") == [
        ["file", "part", "color", "session"],
        ["crops/s1/a_1.jpg", "brick-2x4", "light-gray", "s1"],
        ["crops/s2/b_1.jpg", "other", "", "s2"],
    ]
    assert (layout.root / "crops/s1/a_1.jpg").exists()


def test_changing_and_forgetting_an_answer_rewrites_the_file(layout):
    labels = Labels(layout)
    labels.save("rina", "crops/s1/a_1.jpg", "brick-2x4", "red")

    labels.save("rina", "crops/s1/a_1.jpg", "plate-2x4", "red")
    assert rows(layout.labels / "rina.csv")[1][:3] == ["crops/s1/a_1.jpg", "plate-2x4", "red"]

    labels.save("rina", "crops/s1/a_1.jpg", None, None)  # undo of a first answer
    assert rows(layout.labels / "rina.csv") == [["file", "part", "color", "session"]]


def test_answers_survive_a_restart_and_stay_per_labeler(layout):
    Labels(layout).save("rina", "crops/s1/a_2.jpg", "", "blue")

    again = Labels(layout)
    assert again.start("rina")["answers"] == {"crops/s1/a_2.jpg": {"part": "", "color": "blue"}}
    assert again.start("budi")["answers"] == {}
    assert again.labelers() == ["budi", "rina"]


@pytest.mark.parametrize(
    ("name", "file", "part", "color"),
    [
        ("rina", "crops/s1/missing.jpg", "brick-1x1", "red"),
        ("rina", "crops/s1/a_1.jpg", "brick-9x9", "red"),
        ("rina", "crops/s1/a_1.jpg", "brick-1x1", "purple"),
        ("rina", "crops/s1/a_1.jpg", "brick-1x1", None),
        ("../rina", "crops/s1/a_1.jpg", "brick-1x1", "red"),
        ("Rina", "crops/s1/a_1.jpg", "brick-1x1", "red"),
    ],
)
def test_bad_answers_are_refused(layout, name, file, part, color):
    with pytest.raises(LabelError):
        Labels(layout).save(name, file, part, color)
    assert not layout.labels.exists()  # nothing written


def test_the_page_never_gets_scores_or_predictions(layout):
    crops = Labels(layout).start("rina")["crops"]

    assert set(crops[0]) == {"file", "session", "photo", "preview", "n", "size", "box"}
    assert crops[0]["box"] == [5, 5, 55, 55]
