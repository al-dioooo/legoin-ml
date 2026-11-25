"""`cut --predict`'s ports. They need tools/labeler/requirements.txt, which CI doesn't install."""

import pytest

pytest.importorskip("torch")
pytest.importorskip("sklearn")
pytest.importorskip("skimage")

from PIL import Image

from tools.labeler.predict import brick_color, check_catalogue, name_colors

# legoin_warna.json from release v0.2.0, the keys the color step reads.
COLORS = {
    "colors": ["red", "blue", "yellow", "green", "black", "white", "light-gray", "dark-gray", "orange", "brown"],
    "reference_lab": {
        "red": [43.033, 63.794, 53.71], "blue": [38.299, 21.223, -61.285],
        "yellow": [83.347, -1.357, 73.766], "green": [44.477, -38.29, 23.044],
        "black": [5.299, -1.658, -8.371], "white": [100.0, -0.002, 0.005],
        "light-gray": [67.463, -0.99, -2.68], "dark-gray": [46.096, -1.981, 3.078],
        "orange": [68.982, 37.677, 71.211], "brown": [22.913, 19.145, 24.664],
    },
    "temperature": 6.5707, "max_delta_e": 29.379, "neutral_chroma": 15, "kmeans_k": 4,
    "kmeans_n_init": 2, "kmeans_random_state": 0, "analysis_size": 96,
    "lightness_percentile": 75, "border_fraction": 0.08, "centre_sigma": 0.3,
}
LABELS = {
    "classes": ["brick-1x1", "brick-1x2", "brick-1x3", "brick-1x4", "brick-2x2", "brick-2x3", "brick-2x4",
                "plate-1x2", "plate-2x2", "plate-2x4", "slope-2x2", "tile-1x2", "round-1x1"],
    "num_outputs": 14,
}


def brick(rgb):
    """A brick filling the middle of a light crop, as the widened box cuts it."""
    crop = Image.new("RGB", (100, 80), (245, 245, 245))
    crop.paste(Image.new("RGB", (70, 50), rgb), (15, 15))
    return crop


@pytest.mark.parametrize(
    ("rgb", "expected"), [((201, 26, 9), "red"), ((0, 85, 191), "blue"), ((242, 205, 55), "yellow")]
)
def test_the_color_port_names_catalogue_colors_like_legoin_api(rgb, expected):
    import numpy as np

    ids, confidence = name_colors(np.atleast_2d(brick_color(brick(rgb), COLORS)), COLORS)

    assert ids == [expected]
    assert confidence[0] >= 0.6


def test_release_files_must_use_the_catalogue():
    check_catalogue(LABELS, COLORS)
    with pytest.raises(SystemExit):
        check_catalogue({**LABELS, "classes": LABELS["classes"][::-1]}, COLORS)
    with pytest.raises(SystemExit):
        check_catalogue(LABELS, {**COLORS, "colors": ["red", "purple"]})
