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

TAG = "v0.2.0"
RELEASE_URL = f"https://github.com/al-dioooo/legoin-ml/releases/download/{TAG}"
DETECTOR = "best.pt"
SHA256 = {DETECTOR: "60f5b3a881b2a289aa2de86f7e1695cb68d8e63c91687e1722c6454fb00b2a21"}
ATTEMPTS = 3


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
