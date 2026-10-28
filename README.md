# legoin-ml

The models behind Legoin: notebooks that train and evaluate them, and the weights the backend will serve. Product docs, team guidelines and decisions live in [legoin-docs](https://github.com/al-dioooo/legoin-docs); the web app is [legoin-web](https://github.com/al-dioooo/legoin-web).

A Legoin scan runs in stages:

1. **Detection** finds every brick in one photo with YOLO11 and a single `lego` class. The box count is the first inventory.
2. **Part classification** names each cropped brick. Planned.
3. **Color** reads each brick's color from its crop. Planned.

## Notebooks

| Notebook | What it does |
| --- | --- |
| [01-yolo11-brick-detection](notebooks/01-yolo11-brick-detection.ipynb) [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/al-dioooo/legoin-ml/blob/main/notebooks/01-yolo11-brick-detection.ipynb) | Stage 1. Converts the dataset's PASCAL VOC boxes to YOLO labels, trains YOLO11n, reports mAP, precision and recall on the test split, checks how well the box count matches the real brick count, and saves brick crops for stage 2. |

The notebooks are written in Indonesian, since they double as coursework for Visual Komputer Cerdas at IPB University.

## Dataset

Stage 1 trains on *Tagged images with LEGO bricks*: 2,933 photos holding 1 to 32 bricks and 2,908 single-brick renders, with boxes in PASCAL VOC format.

> Zawora, K., Zaraziński, S., Śledź, B., & Łobacz, B. (2021). *Tagged images with LEGO bricks*. MOST Wiedzy, Gdańsk University of Technology. <https://doi.org/10.34808/anq4-rn44>

The dataset is licensed CC BY 4.0, so anything built on it credits the source. The notebook downloads the zip (about 6 GB) itself; the data is never committed.

## Tech stack

- Python 3.12
- [Ultralytics](https://docs.ultralytics.com) 8.4.190 (YOLO11) on PyTorch
- pandas, matplotlib and Pillow for data exploration
- Google Colab with a T4 GPU for training
- [Ruff](https://docs.astral.sh/ruff/) for linting and nbformat for notebook checks

## Setup and run

**Colab (recommended).** Open a notebook from its badge, pick *Runtime → Change runtime type → T4 GPU*, then *Run all*. Data goes to the Colab disk. Training runs and the best weights are saved to Google Drive under `MyDrive/VISKOM_Kelompok5`.

**Locally.** Needs Python 3.12 and, for a full training run, an NVIDIA GPU.

```bash
python -m venv .venv
source .venv/bin/activate
pip install jupyterlab
jupyter lab
```

The notebook's first cell installs its own dependencies. Outside Colab it writes `data/` and `runs/` next to the notebook, and git ignores both. On a headless Linux server, replace `opencv-python` with `opencv-python-headless` if importing Ultralytics fails on `libGL.so.1`.

## Checks

```bash
pip install -r requirements-dev.txt
ruff check .
python scripts/check_repo.py
```

`check_repo.py` fails when a notebook is invalid or still holds outputs, or when data or weights are in the repository. `python scripts/check_repo.py --fix` clears notebook outputs in place. CI runs both commands on every pull request.

## Environment variables

None. The notebooks need no keys or tokens.

## Model releases

Weights are published as [GitHub Releases](https://github.com/al-dioooo/legoin-ml/releases), never committed. Each release carries the `.pt` file, the training config and the test metrics: mAP@50, mAP@50-95, precision, recall and count MAE. There are none yet; the first full training run on Colab becomes `v0.1.0`.

## Contributing

Read [AGENTS.md](AGENTS.md) before opening a pull request. It summarizes the [legoin-docs guidelines](https://github.com/al-dioooo/legoin-docs/tree/main/guidelines) for this repository: work on a branch, write Conventional Commits, merge through a pull request linked to an issue, and clear notebook outputs before committing.
