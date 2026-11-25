"""`cut`: stage 1 crops of the team's photos, made the way legoin-api makes them.

For each photo in `photos/<session>/` that isn't cut yet, it applies the EXIF orientation,
runs release v0.2.0's detector with the settings from its notes, and saves each widened box
as `crops/<session>/<photo stem>_<n>.jpg`, numbered top to bottom, then left to right. It also
saves an upright copy of the photo in `preview/` for the labeling page.

`crops/manifest.csv` has one row per crop and `crops/photos.csv` one row per photo cut, so a
rerun skips the photos already cut. Both are rewritten after every photo.
"""

import hashlib
import os
import urllib.request
from pathlib import Path

# Before Ultralytics loads: no analytics, update checks or downloads. Photos never leave this
# machine; the only download is the release's weights, below.
os.environ["YOLO_OFFLINE"] = "1"

from PIL import Image, ImageOps
from ultralytics import YOLO

from .crops import crop_name, reading_order, widen
from .files import (
    MANIFEST_FIELDS,
    PHOTO_FIELDS,
    PHOTO_SUFFIXES,
    Layout,
    read_csv,
    write_csv,
)

TAG = "v0.2.0"
RELEASE_URL = f"https://github.com/al-dioooo/legoin-ml/releases/download/{TAG}"
DETECTOR = "best.pt"
SHA256 = {DETECTOR: "60f5b3a881b2a289aa2de86f7e1695cb68d8e63c91687e1722c6454fb00b2a21"}
ATTEMPTS = 3

# Stage 1's settings from the v0.2.0 release notes, as legoin-api predicts.
IMGSZ, CONF, IOU, MAX_DET = 640, 0.65, 0.7, 300
# Ultralytics' save_one_box writes crops this way.
CROP_JPEG = {"quality": 95, "subsampling": 0}
PREVIEW_SIZE = 1600


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_file(name: str, folder: Path) -> Path:
    """A file of the release, downloaded once and never used unless its SHA-256 matches."""
    path = folder / TAG / name
    if path.exists() and sha256(path) == SHA256[name]:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{RELEASE_URL}/{name}"
    partial = path.with_name(name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "legoin-labeler"})
    for attempt in range(1, ATTEMPTS + 1):
        print(f"Downloading {url}")
        try:
            with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as file:
                while chunk := response.read(1 << 20):
                    file.write(chunk)
            break
        except OSError as error:
            partial.unlink(missing_ok=True)
            if attempt == ATTEMPTS:
                raise SystemExit(f"Couldn't download {url}: {error}") from error
            print(f"Download failed ({error}); trying again.")
    if (actual := sha256(partial)) != SHA256[name]:
        partial.unlink()
        raise SystemExit(f"{url} has SHA-256 {actual}, not {SHA256[name]}; not using it.")
    partial.replace(path)
    return path


def photos_to_cut(layout: Layout, done: set[str]) -> list[tuple[str, Path]]:
    """(session, photo) for every photo in a session folder that isn't cut yet."""
    if not layout.photos.is_dir():
        raise SystemExit(f"No {layout.photos}: put the photos in {layout.photos}/<session>/.")
    pending = []
    for entry in sorted(layout.photos.iterdir()):
        if not entry.is_dir():
            print(f"Skipping {layout.rel(entry)}: photos go in one folder per session.")
            continue
        photos = []
        for path in sorted(entry.iterdir()):
            if path.suffix.lower() in PHOTO_SUFFIXES:
                photos.append(path)
            elif path.is_file() and not path.name.startswith("."):
                print(f"Skipping {layout.rel(path)}: not JPEG, PNG or WebP.")
        stems = [p.stem for p in photos]
        if clash := sorted({s for s in stems if stems.count(s) > 1}):
            raise SystemExit(f"Photos in {entry.name} share a name, so their crops would too: {clash}")
        pending += [(entry.name, p) for p in photos if layout.rel(p) not in done]
    return pending


def cut_photo(model: YOLO, layout: Layout, session: str, path: Path) -> tuple[dict, list[dict]]:
    """Cuts one photo: its photos.csv row and its manifest rows."""
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    result = model.predict(
        image, imgsz=IMGSZ, conf=CONF, iou=IOU, max_det=MAX_DET, device="cpu", verbose=False
    )[0]
    boxes = result.boxes.xyxy.cpu().numpy().tolist()
    scores = result.boxes.conf.cpu().numpy().tolist()

    preview = layout.previews / session / f"{path.stem}.jpg"
    preview.parent.mkdir(parents=True, exist_ok=True)
    small = image.copy()
    small.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE))
    small.save(preview, quality=85)  # a new JPEG: no EXIF, so no location or camera data

    rows = []
    for n, i in enumerate(reading_order(boxes), start=1):
        box = widen(boxes[i], image.width, image.height)
        file = layout.crops / session / crop_name(path.stem, n)
        file.parent.mkdir(parents=True, exist_ok=True)
        image.crop(box).save(file, **CROP_JPEG)
        rows.append({
            "file": layout.rel(file), "session": session, "photo": layout.rel(path),
            "preview": layout.rel(preview), "width": image.width, "height": image.height,
            "n": n, "score": round(scores[i], 4),
            **{k: round(v, 2) for k, v in zip(("x1", "y1", "x2", "y2"), boxes[i], strict=True)},
            **dict(zip(("crop_x1", "crop_y1", "crop_x2", "crop_y2"), box, strict=True)),
        })
    photo = {
        "photo": layout.rel(path), "session": session, "width": image.width,
        "height": image.height, "crops": len(rows), "model": TAG,
    }
    return photo, rows


def cut(layout: Layout, models: Path) -> None:
    photos = read_csv(layout.photo_list)
    manifest = read_csv(layout.manifest)
    pending = photos_to_cut(layout, {p["photo"] for p in photos})
    print(f"{len(photos)} photos already cut, {len(pending)} to cut.")
    if not pending:
        return
    model = YOLO(str(release_file(DETECTOR, models)), task="detect")
    for k, (session, path) in enumerate(pending, start=1):
        photo, rows = cut_photo(model, layout, session, path)
        # Whole files after every photo: an interrupted run leaves no half-recorded photo.
        manifest = [r for r in manifest if r["photo"] != photo["photo"]] + rows
        manifest.sort(key=lambda r: (r["session"], r["photo"], int(r["n"])))
        photos.append(photo)
        write_csv(layout.manifest, MANIFEST_FIELDS, manifest)
        write_csv(layout.photo_list, PHOTO_FIELDS, photos)
        print(f"[{k}/{len(pending)}] {photo['photo']}: {len(rows)} crops")
    print(f"{len(manifest)} crops in {layout.rel(layout.manifest)}")
