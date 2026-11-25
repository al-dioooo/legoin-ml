"""The tool's folders under the data root, and the CSV files it reads and writes.

The data root is notebooks 02 and 03's `data/foto_mandiri`. Run locally, the notebooks look
for it next to themselves, so it defaults to `notebooks/data/foto_mandiri` here. Git ignores
every `data/` folder, so photos, crops and labels are never committed.

Needs only the standard library, so `label` and `merge` run on a bare Python.
"""

import csv
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "notebooks" / "data" / "foto_mandiri"

PHOTO_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")

# One row per crop. Paths are relative to the data root, like `file` in label.csv. The box is
# the detector's, in pixels of the upright photo; the crop box is the widened one that was cut.
MANIFEST_FIELDS = [
    "file", "session", "photo", "preview", "width", "height", "n", "score",
    "x1", "y1", "x2", "y2", "crop_x1", "crop_y1", "crop_x2", "crop_y2",
]
# One row per photo cut, including photos where the detector found nothing.
PHOTO_FIELDS = ["photo", "session", "width", "height", "crops", "model"]


class Layout:
    """Every path the tool uses, from the data root."""

    def __init__(self, root: Path):
        self.root = root
        self.photos = root / "photos"            # photos/<session>/<photo>, from the team
        self.crops = root / "crops"              # crops/<session>/<photo stem>_<n>.jpg
        self.previews = root / "preview"         # preview/<session>/<photo stem>.jpg, upright
        self.labels = root / "labels"            # labels/<name>.csv, one per labeler
        self.manifest = self.crops / "manifest.csv"
        self.photo_list = self.crops / "photos.csv"
        self.label_csv = root / "label.csv"      # what notebooks 02 and 03 read

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()


def read_csv(path: Path) -> list[dict[str, str]]:
    """The rows of a CSV with a header, or no rows if the file doesn't exist yet."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fields: list[str], rows: Iterable[dict]) -> None:
    """Replaces the whole file at once, so a crash or a closed tab never leaves half a CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
