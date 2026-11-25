"""`label`: a local page where one person labels each crop's part and color.

The page is served on 127.0.0.1 only, with the standard library. Each labeler's answers go to
`labels/<name>.csv` as soon as a crop is answered, in label.csv's format: `file,part,color`
plus `session`, where an empty part or color means doubtful. A row is one answered crop.

The page gets the crops, their photos and boxes, never the detector score or v0.2.0's
predictions, so nothing nudges the labeler.
"""

import re
import threading
from pathlib import Path

from .catalogue import (
    COLOR_VALUES,
    COLORS,
    OTHER,
    PART_VALUES,
    PARTS,
    TARGET,
    TARGET_OTHER,
)
from .files import Layout, read_csv, write_csv

LABEL_FIELDS = ["file", "part", "color", "session"]
NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
PAGE = Path(__file__).parent / "page"
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


class LabelError(ValueError):
    """A request the page should never send: an unknown crop, name or value."""


class Labels:
    """The crops, and every labeler's answers, saved to labels/<name>.csv on each change."""

    def __init__(self, layout: Layout):
        self.layout = layout
        self.crops = {row["file"]: row for row in read_csv(layout.manifest)}
        self.order = {file: i for i, file in enumerate(self.crops)}
        # The only files the page may load: the crops and their photos' previews.
        self.images = set(self.crops) | {row["preview"] for row in self.crops.values()}
        self.answers: dict[str, dict[str, dict]] = {}
        self.lock = threading.Lock()

    def path(self, name: str) -> Path:
        if not NAME.match(name):
            raise LabelError(f"Bad name {name!r}: lowercase letters, digits, - and _ only.")
        return self.layout.labels / f"{name}.csv"

    def of(self, name: str) -> dict[str, dict]:
        if name not in self.answers:
            self.answers[name] = {row["file"]: row for row in read_csv(self.path(name))}
        return self.answers[name]

    def labelers(self) -> list[str]:
        names = {p.stem for p in self.layout.labels.glob("*.csv")} | set(self.answers)
        return sorted(n for n in names if NAME.match(n))

    def save(self, name: str, file: str, part: str | None, color: str | None) -> None:
        """Answers a crop, or forgets its answer when part and color are None (undo)."""
        if file not in self.crops:
            raise LabelError(f"Unknown crop {file!r}.")
        if (part is None) != (color is None):
            raise LabelError("A crop is answered with both a part and a color.")
        if part is not None and (part not in PART_VALUES or color not in COLOR_VALUES):
            raise LabelError(f"Unknown part {part!r} or color {color!r}.")
        with self.lock:
            answers = self.of(name)
            if part is None:
                answers.pop(file, None)
            else:
                session = self.crops[file]["session"]
                answers[file] = {"file": file, "part": part, "color": color, "session": session}
            rows = sorted(answers.values(), key=lambda r: self.order.get(r["file"], len(self.order)))
            write_csv(self.path(name), LABEL_FIELDS, rows)

    def start(self, name: str) -> dict:
        """Everything the page needs for one labeler."""
        crops = [
            {
                "file": c["file"], "session": c["session"], "photo": c["photo"],
                "preview": c["preview"], "n": int(c["n"]),
                "size": [int(c["width"]), int(c["height"])],
                "box": [int(c[k]) for k in ("crop_x1", "crop_y1", "crop_x2", "crop_y2")],
            }
            for c in self.crops.values()
        ]
        answers = {f: {"part": r["part"], "color": r["color"]} for f, r in self.of(name).items()}
        return {
            "name": name, "crops": crops, "answers": answers,
            "parts": [{"id": p, "design": d} for p, d in PARTS.items()],
            "colors": [{"id": c, "rgb": rgb, "name": n} for c, (rgb, n) in COLORS.items()],
            "other": OTHER, "target": TARGET, "target_other": TARGET_OTHER,
        }
