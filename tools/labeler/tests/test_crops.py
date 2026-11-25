import os

import numpy as np
import pytest

from tools.labeler.crops import crop_name, reading_order, widen


# Expected crop boxes from legoin-api's widen() (src/legoin_api/pipeline/models.py at b084247).
@pytest.mark.parametrize(
    ("box", "size", "expected"),
    [
        ((100.0, 50.0, 200.0, 150.0), (640, 480), (94, 44, 206, 156)),
        ((12.34, 56.78, 90.12, 345.67), (640, 480), (6, 48, 95, 353)),
        # Past the top-left corner: truncated toward zero, then clipped.
        ((3.5, 2.25, 40.75, 30.5), (640, 480), (0, 0, 46, 35)),
        # Past the bottom-right corner: clipped to the photo.
        ((600.0, 440.0, 639.0, 479.0), (640, 480), (594, 434, 640, 480)),
        ((0.0, 0.0, 640.0, 480.0), (640, 480), (0, 0, 640, 480)),
        # Boxes where float64 math would cut one pixel off: right 2264, bottom 1356, left 1735.
        (
            (2020.6849365234375, 2573.871826171875, 2257.63037109375, 3084.00830078125),
            (4032, 3024),
            (2013, 2563, 2265, 3024),
        ),
        (
            (168.4712677001953, 1126.0731201171875, 253.9686279296875, 1349.7630615234375),
            (4032, 3024),
            (162, 1118, 259, 1357),
        ),
        (
            (1741.3966064453125, 2573.388916015625, 1781.0587158203125, 3007.15771484375),
            (4032, 3024),
            (1736, 2564, 1786, 3016),
        ),
    ],
)
def test_widen_matches_legoin_api(box, size, expected):
    assert widen(box, *size) == expected


def test_widen_matches_ultralytics_save_one_box():
    """Only where `cut`'s requirements are installed; CI installs the dev tools alone."""
    os.environ["YOLO_OFFLINE"] = "1"
    pytest.importorskip("ultralytics")
    import torch
    from PIL import Image
    from ultralytics.utils.plotting import save_one_box

    rng = np.random.default_rng(0)
    rgb = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
    photo, bgr = Image.fromarray(rgb), np.ascontiguousarray(rgb[:, :, ::-1])
    for _ in range(500):
        x1, y1 = rng.uniform(-20, 640), rng.uniform(-20, 480)
        box = np.array([x1, y1, x1 + rng.uniform(1, 300), y1 + rng.uniform(1, 300)], np.float32)
        reference = save_one_box(torch.tensor(box), bgr, save=False)
        assert np.array_equal(np.asarray(photo.crop(widen(box, 640, 480))), reference)


def test_crops_are_numbered_top_to_bottom_then_left_to_right():
    # In the detector's order, by score.
    boxes = [(300, 10, 340, 50), (10, 200, 50, 240), (10, 10, 50, 50), (150, 200, 190, 240)]

    order = reading_order(boxes)

    assert order == [2, 0, 1, 3]
    assert [crop_name("IMG_0001", n) for n, _ in enumerate(order, 1)][:2] == [
        "IMG_0001_1.jpg",
        "IMG_0001_2.jpg",
    ]
