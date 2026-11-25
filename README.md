# legoin-ml

The models behind Legoin: notebooks that train and evaluate them, and the weights the backend will serve. Product docs, team guidelines and decisions live in [legoin-docs](https://github.com/al-dioooo/legoin-docs); the web app is [legoin-web](https://github.com/al-dioooo/legoin-web).

A Legoin scan runs in stages:

1. **Detection** finds every brick in one photo with YOLO11 and a single `lego` class. The box count is the first inventory.
2. **Part classification** names each cropped brick as one of the 13 catalogue parts with MobileNetV3-Large, or flags it for checking.
3. **Color** reads each brick's color from its crop as one of the 10 catalogue colors, or flags it for checking.

## Notebooks

| Notebook | What it does |
| --- | --- |
| [01-yolo11-brick-detection](notebooks/01-yolo11-brick-detection.ipynb) [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/al-dioooo/legoin-ml/blob/main/notebooks/01-yolo11-brick-detection.ipynb) | Stage 1. Converts the dataset's PASCAL VOC boxes to YOLO labels, trains YOLO11n, reports mAP, precision and recall on the test split, checks how well the box count matches the real brick count, and saves brick crops for stage 2. |
| [02-mobilenetv3-part-classification](notebooks/02-mobilenetv3-part-classification.ipynb) [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/al-dioooo/legoin-ml/blob/main/notebooks/02-mobilenetv3-part-classification.ipynb) | Stage 2. Downloads only the 13 catalogue parts and a sample of other parts from the classification dataset, fine-tunes MobileNetV3-Large with an extra `other` output, calibrates confidence on val, reports top-1 accuracy on held-out real photos, and exports the weights with a label map that uses the API contract's part ids. |
| [03-kmeans-cielab-brick-color](notebooks/03-kmeans-cielab-brick-color.ipynb) [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/al-dioooo/legoin-ml/blob/main/notebooks/03-kmeans-cielab-brick-color.ipynb) | Stage 3. Separates the brick from its background with K-Means in CIELAB and names its color by the nearest catalogue reference (CIEDE2000), flagging colors outside the catalogue. It evaluates on renders whose file names carry their color, evaluates the team's labeled phone crops when they exist, and saves the color parameters for the backend. Runs on a CPU. |

The notebooks are written in Indonesian, since they double as coursework for Visual Komputer Cerdas at IPB University.

## Dataset

Stage 1 trains on *Tagged images with LEGO bricks*: 2,933 photos holding 1 to 32 bricks and 2,908 single-brick renders, with boxes in PASCAL VOC format.

> Zawora, K., Zaraziński, S., Śledź, B., & Łobacz, B. (2021). *Tagged images with LEGO bricks*. MOST Wiedzy, Gdańsk University of Technology. <https://doi.org/10.34808/anq4-rn44>

The dataset is licensed CC BY 4.0, so anything built on it credits the source. The notebook downloads the zip (about 6 GB) itself; the data is never committed.

Stage 2 trains on *LEGO bricks for training classification network*: 447 part types in folders named by LEGO design id, with about 53,000 real photos and 568,000 renders, all single bricks on a white background.

> Boiński, T. M., Zaraziński, S., & Śledź, B. (2021). *LEGO bricks for training classification network* (version 1.1). MOST Wiedzy, Gdańsk University of Technology. <https://doi.org/10.34808/rcza-jy08>

It is licensed CC BY 4.0. Its zip is 6 GB, but the notebook reads the zip's index over HTTP range requests and downloads only the folders it uses, about 350 MB. Its real photos are studio shots, so they don't measure accuracy on phone photos; the notebook explains how the team can label its own crops for that.

*B200C LEGO Classification* (Kaggle, CC BY-SA 4.0) is a documented option in notebook 02 and isn't used by default, because downloading it needs a Kaggle account.

Stage 3 starts from Rebrickable's RGB values for the 10 catalogue colors (<https://rebrickable.com/colors/>). It tests the method on the renders of the same *LEGO bricks for training classification network* (CC BY 4.0, cited above), whose file names carry the brick's LEGO color name, and downloads only the folders it uses. No public dataset labels real photos with the catalogue colors, so color accuracy on phone photos needs crops the team labels itself; notebook 03 explains how.

## Tech stack

- Python 3.12
- [Ultralytics](https://docs.ultralytics.com) 8.4.190 (YOLO11) on PyTorch
- PyTorch 2.15.0 and torchvision 0.29.2 for MobileNetV3-Large (stage 2)
- scikit-image 0.26.0 and scikit-learn 1.9.1 for K-Means and CIELAB color matching (stage 3)
- pandas, matplotlib and Pillow for data exploration
- Google Colab with a T4 GPU for training
- [Ruff](https://docs.astral.sh/ruff/) for linting, nbformat for notebook checks and pytest for the labeling tool

## Setup and run

**Colab (recommended).** Open a notebook from its badge, pick *Runtime → Change runtime type → T4 GPU*, then *Run all*. Data goes to the Colab disk. Training runs and the best weights are saved to Google Drive under `MyDrive/VISKOM_Kelompok5`.

**Locally.** Needs Python 3.12. A full training run is fastest on an NVIDIA GPU, but a CPU works too: `v0.1.0` trained 35 epochs in about 4 hours on a 16-vCPU server.

```bash
python -m venv .venv
source .venv/bin/activate
pip install jupyterlab
jupyter lab
```

The notebook's first cell installs its own dependencies. Outside Colab it writes `data/` and `runs/` next to the notebook, and git ignores both. On a headless Linux server, replace `opencv-python` with `opencv-python-headless` if importing Ultralytics fails on `libGL.so.1`.

## Labeling your own photos

The PRD's part and color targets (at least 85%) are about crops from phone photos, and no public dataset has those. So the team photographs its own bricks, and `tools/labeler` turns the photos into the labeled crops that notebook 02 (section 10) and notebook 03 (section 8.2) read: `data/foto_mandiri/label.csv`, with columns `file,part,color`. Everything runs on your own machine. Photos are never uploaded, and the only download is the detector from release `v0.2.0`.

**Shoot.**

- Aim for about 30 crops of each catalogue part (about 400) plus about 50 pieces outside the catalogue, and at least 30 of each catalogue color plus about 50 in other colors. Each brick counts toward both.
- Leave space between the bricks in a photo, so each one gets its own box.
- Vary the background (wooden table, floor, cloth) and the light (daylight by a window, a white lamp, a yellow lamp). Take some photos slightly tilted so the sides show: from straight above, a brick and a plate look alike.
- Keep one folder per shooting session: `data/foto_mandiri/photos/<session>/`. `label.csv` carries each crop's session, so the crops of one session can stay in the same split.
- Use JPEG, PNG or WebP. HEIC isn't read, so on an iPhone set *Settings → Camera → Formats* to *Most Compatible*.

**Cut.** Install the tool's requirements once, then cut:

```bash
pip install -r tools/labeler/requirements.txt
python -m tools.labeler cut
```

`cut` downloads `best.pt` from release `v0.2.0` once and checks its SHA-256. It then runs the detector on every photo that isn't cut yet, with the release's settings (`imgsz` 640, `conf` 0.65), after applying the photo's EXIF orientation. Each box is widened exactly as legoin-api and Ultralytics' `save_crop` do, and saved as `crops/<session>/<photo>_<n>.jpg`, numbered top to bottom. `crops/manifest.csv` lists each crop's photo, session, box and detector score. After you add photos, run it again; it skips the photos already cut.

**Label.** Two team members each label every crop, on their own, without seeing each other's answers:

```bash
python -m tools.labeler label
```

The page opens at <http://127.0.0.1:8765/> and asks for your name. It shows each crop large next to its photo, with the box drawn. Pick the part, then the color, with the keys on the buttons or with the mouse:

- `O` marks a piece or a color outside the catalogue (`other`).
- `X` marks the field doubtful and leaves it empty, so the notebooks skip that crop for that stage.
- `Z` undoes, and the arrow keys move between crops.

Answers go to `labels/<name>.csv` after every crop, so closing the tab loses nothing. Progress bars count your crops against the targets. The page tells you to label from the brick in your hand, not only the photo, and which pairs are often mixed up. It never shows the models' guesses. `label` needs only Python 3.12, with nothing to install, so a labeler can work on their own computer with a copy of the repository and of the data root's `crops/` and `preview/` folders.

The data root defaults to `notebooks/data/foto_mandiri`, where the notebooks look when they run locally; `--root` picks another folder. Git ignores it, like every `data/` folder. On Colab, upload the folder to `/content/data/foto_mandiri`; the crops and `label.csv` are enough.

## Checks

```bash
pip install -r requirements-dev.txt
ruff check .
python scripts/check_repo.py
python -m pytest tools
```

`check_repo.py` fails when a notebook is invalid or still holds outputs, or when data or weights are in the repository. `python scripts/check_repo.py --fix` clears notebook outputs in place. `pytest` runs the labeling tool's tests; the one that compares crops with Ultralytics runs only where `tools/labeler/requirements.txt` is installed. CI runs all three commands on every pull request.

## Environment variables

None by default; the notebooks need no keys or tokens.

| Variable | Used for |
| --- | --- |
| `KAGGLE_USERNAME`, `KAGGLE_KEY` | Optional. Only to add B200C to stage 2 training by hand. On Colab, store them as Colab secrets; never write them in a notebook. |

## Model releases

Weights are published as [GitHub Releases](https://github.com/al-dioooo/legoin-ml/releases), never committed. Each release carries the `.pt` file, the training config and the test metrics: mAP@50, mAP@50-95, precision, recall and count MAE for the detector. A part classifier release also carries `legoin_mobilenetv3_part_labels.json`, which gives the class order, input size, normalization and confidence temperature the backend must use, and reports top-1 accuracy with the kind of photos it was measured on. The color step has no weights; its parameters file, `legoin_warna.json`, ships in a release the same way. From v0.2.0, a release carries the files for every stage, so the backend pins one tag and predicts with the settings given in its notes.

| Release | Contents | Trained | Test results | Backend settings |
| --- | --- | --- | --- | --- |
| [v0.1.0](https://github.com/al-dioooo/legoin-ml/releases/tag/v0.1.0) | Detector: YOLO11n, 1 class | 35 epochs on a CPU server, 4.1 h | mAP@50 0.992, count MAE 0.055 | `imgsz` 640, `conf` 0.65 |
| [v0.2.0](https://github.com/al-dioooo/legoin-ml/releases/tag/v0.2.0) | v0.1.0's detector, unchanged; part classifier: MobileNetV3-Large, 13 parts plus `other`; color parameters, provisional | Classifier: 15 epochs on a CPU server, 1.8 h | Classifier top-1 97.7% on studio photos, an upper bound; color not yet measured on photos | Detector as in v0.1.0; classifier 224 px letterbox, temperature 0.7493 |

The PRD targets are mAP@50 ≥ 0.85, a count MAE of at most 1 brick per photo, and at least 85% accuracy for parts and for colors on real-photo crops. The classifier's test photos are studio shots, so its number is an upper bound until the team's labeled phone crops exist.

## Contributing

Read [AGENTS.md](AGENTS.md) before opening a pull request. It summarizes the [legoin-docs guidelines](https://github.com/al-dioooo/legoin-docs/tree/main/guidelines) for this repository: work on a branch, write Conventional Commits, merge through a pull request linked to an issue, and clear notebook outputs before committing.
