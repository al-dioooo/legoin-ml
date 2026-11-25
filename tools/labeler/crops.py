"""Stage 1's crop: the detector's box widened the way Ultralytics' `save_one_box` cuts it.

The same math as legoin-api's `widen()` in `src/legoin_api/pipeline/models.py`, which the
part classifier's crop check also used: 1.02× plus 10 px around the box centre, in float32 as
Ultralytics computes it, truncated toward zero, then clipped to the photo.
"""

from collections.abc import Sequence

import numpy as np

GAIN = 1.02
PAD = 10


def widen(box: Sequence[float], width: int, height: int) -> tuple[int, int, int, int]:
    """The crop box (left, top, right, bottom) for a detector box (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = np.array(box, dtype=np.float32)
    cx, cy = (x1 + x2) / np.float32(2), (y1 + y2) / np.float32(2)
    w = (x2 - x1) * np.float32(GAIN) + np.float32(PAD)
    h = (y2 - y1) * np.float32(GAIN) + np.float32(PAD)
    half_w, half_h = w / np.float32(2), h / np.float32(2)
    left, top, right, bottom = (int(v) for v in (cx - half_w, cy - half_h, cx + half_w, cy + half_h))
    return (
        min(max(left, 0), width),
        min(max(top, 0), height),
        min(max(right, 0), width),
        min(max(bottom, 0), height),
    )


def reading_order(boxes: Sequence[Sequence[float]]) -> list[int]:
    """The boxes' indexes top to bottom, then left to right, so numbers don't follow scores."""
    return sorted(range(len(boxes)), key=lambda i: (boxes[i][1], boxes[i][0], boxes[i][3], boxes[i][2]))


def crop_name(photo_stem: str, n: int) -> str:
    """`<photo stem>_<n>.jpg`, with n counting from 1 in reading order."""
    return f"{photo_stem}_{n}.jpg"
