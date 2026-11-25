"""`label`: a local page where one person labels each crop's part and color.

The page is served on 127.0.0.1 only, with the standard library. Each labeler's answers go to
`labels/<name>.csv` as soon as a crop is answered, in label.csv's format: `file,part,color`
plus `session`, where an empty part or color means doubtful. A row is one answered crop.

The page gets the crops, their photos and boxes, never the detector score or v0.2.0's
predictions, so nothing nudges the labeler.
"""

import json
import re
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

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


class Handler(BaseHTTPRequestHandler):
    labels: Labels
    port: int

    def do_GET(self) -> None:
        if not self.from_this_machine():
            return
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        if url.path in STATIC:
            name, kind = STATIC[url.path]
            self.send(HTTPStatus.OK, (PAGE / name).read_bytes(), kind)
        elif url.path == "/api/labelers":
            self.send_json({"labelers": self.labels.labelers(), "crops": len(self.labels.crops)})
        elif url.path == "/api/start":
            self.answer(lambda: self.labels.start(query.get("name", [""])[0]))
        elif url.path.startswith("/data/") and unquote(url.path[6:]) in self.labels.images:
            data = (self.labels.layout.root / unquote(url.path[6:])).read_bytes()
            self.send(HTTPStatus.OK, data, "image/jpeg", cache="max-age=3600")
        else:
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if not self.from_this_machine():
            return
        # JSON only: a form on another website can't post JSON here without the browser asking.
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self.send_json({"error": "JSON only"}, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if urlsplit(self.path).path == "/api/answer":
            self.answer(lambda: self.labels.save(
                body.get("name", ""), body.get("file", ""), body.get("part"), body.get("color")
            ) or {"ok": True})
        else:
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def from_this_machine(self) -> bool:
        # Refuses pages that reach this server through another host name (DNS rebinding).
        if self.headers.get("Host") in {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}:
            return True
        self.send_json({"error": "open the page at 127.0.0.1"}, HTTPStatus.FORBIDDEN)
        return False

    def answer(self, make) -> None:
        try:
            self.send_json(make())
        except LabelError as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except OSError as error:  # e.g. the CSV is open in a spreadsheet on Windows
            self.send_json({"error": f"Can't write the labels: {error}"}, HTTPStatus.CONFLICT)

    def send_json(self, data, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send(status, json.dumps(data).encode(), "application/json")

    def send(self, status: HTTPStatus, body: bytes, kind: str, cache: str = "no-store") -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # the base class names it `format`
        pass  # one line per image is noise; errors reach the page


def make_server(labels: Labels, port: int) -> ThreadingHTTPServer:
    """A server on 127.0.0.1 only; port 0 picks a free one."""
    handler = type("BoundHandler", (Handler,), {"labels": labels})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    handler.port = server.server_address[1]
    return server


def serve(layout: Layout, port: int, open_browser: bool) -> None:
    labels = Labels(layout)
    if not labels.crops:
        raise SystemExit(f"No crops in {layout.manifest}: run `python -m tools.labeler cut` first.")
    try:
        server = make_server(labels, port)
    except OSError as error:
        raise SystemExit(f"Port {port} is busy ({error}); try --port {port + 1}.") from error
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"{len(labels.crops)} crops. Labeling page: {url} (Ctrl+C to stop)")
    print(f"Answers are saved in {layout.labels}/<name>.csv after every crop.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
