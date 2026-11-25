"""Release v0.2.0's own part and color answers for each crop, for the accuracy report later.

`cut --predict` stores them in the manifest's `pred_*` columns. They're made the way legoin-api
makes them (`src/legoin_api/pipeline/models.py` and `color.py`), from the crop cut out of the
upright photo in memory, so they're what the app would have shown:

- part: letterbox to 224 px on (124, 116, 104), ImageNet normalization and
  `softmax(logits / temperature)` over 14 outputs. `pred_part` is the argmax of outputs 0–12,
  the part the API sends, with its probability as `pred_part_conf`; `pred_part_top1` is the
  argmax of all 14, which can be `other`.
- color: notebook 03's `warna_kepingan` and `putuskan` with `legoin_warna.json`.

The labeling page never receives these columns.
"""

import warnings

import numpy as np
from PIL import Image
from skimage.color import deltaE_ciede2000, rgb2lab
from sklearn.cluster import KMeans

from .catalogue import COLORS, PARTS

CLASSIFIER = "legoin_mobilenetv3_part.pt"
LABEL_MAP = "legoin_mobilenetv3_part_labels.json"
COLOR_PARAMETERS = "legoin_warna.json"
# From the v0.2.0 release notes, as legoin-api's weights.py has them.
SHA256 = {
    CLASSIFIER: "e8c596a91b85ada2985670e1289a862240f03536456b675e8f691158baaa5e5b",
    LABEL_MAP: "9ead94b90b3254886b79dc545602248e1c2ecc65ac3d65e31daea161601049fc",
    COLOR_PARAMETERS: "bda4af6c3595570274dcb91379571573704c0c42d2b68d7de0a02c216b473634",
}


def check_catalogue(labels: dict, colors: dict) -> None:
    """Refuses release files whose ids aren't the catalogue's the labels use."""
    if labels["classes"] != list(PARTS) or labels["num_outputs"] != len(PARTS) + 1:
        raise SystemExit(f"{LABEL_MAP}'s classes aren't the catalogue's: {labels['classes']}")
    if colors["colors"] != list(COLORS):
        raise SystemExit(f"{COLOR_PARAMETERS}'s colors aren't the catalogue's: {colors['colors']}")


def brick_color(im: Image.Image, p: dict) -> np.ndarray:
    """Notebook 03's `warna_kepingan`: the brick's L*, a*, b* in one crop."""
    im = im.convert("RGB")
    im.thumbnail((p["analysis_size"], p["analysis_size"]))
    lab = rgb2lab(np.asarray(im) / 255.0)
    h, w = lab.shape[:2]
    px = lab.reshape(-1, 3)
    yy, xx = np.mgrid[:h, :w]
    s = p["centre_sigma"]
    centre = np.exp(-(((xx - (w - 1) / 2) / (s * w)) ** 2 + ((yy - (h - 1) / 2) / (s * h)) ** 2) / 2).ravel()
    t = max(1, round(min(h, w) * p["border_fraction"]))
    border = np.ones((h, w), bool)
    border[t : h - t, t : w - t] = False
    border = border.ravel()
    k = p["kmeans_k"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a crop with fewer than k distinct colors
        label = KMeans(k, n_init=p["kmeans_n_init"], random_state=p["kmeans_random_state"]).fit_predict(px)
    score = np.array([centre[label == c].sum() / centre.sum() - (label[border] == c).mean() for c in range(k)])
    brick = np.flatnonzero(score > 0) if (score > 0).any() else [int(score.argmax())]
    f = px[np.isin(label, brick)]
    return np.array([np.percentile(f[:, 0], p["lightness_percentile"]), np.median(f[:, 1]), np.median(f[:, 2])])


def name_colors(lab: np.ndarray, p: dict) -> tuple[list[str], np.ndarray]:
    """Notebook 03's `putuskan`: catalogue color ids and confidences for colors (n, 3)."""
    ref = np.array([p["reference_lab"][c] for c in p["colors"]])
    d = np.stack([deltaE_ciede2000(lab, np.broadcast_to(r, lab.shape)) for r in ref], 1)
    z = -d / p["temperature"]
    prob = np.exp(z - z.max(1, keepdims=True))
    prob /= prob.sum(1, keepdims=True)
    i = prob.argmax(1)
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    neutral = np.hypot(ref[i, 1], ref[i, 2]) < p["neutral_chroma"]
    foreign = (d.min(1) > p["max_delta_e"]) | ((chroma >= p["neutral_chroma"]) & neutral)
    return [p["colors"][k] for k in i], np.where(foreign, np.minimum(prob.max(1), 0.5), prob.max(1))
