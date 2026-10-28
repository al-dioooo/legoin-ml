# AGENTS.md

Rules for anyone changing this repository, people and coding agents alike. They summarize the team guidelines in [legoin-docs/guidelines](https://github.com/al-dioooo/legoin-docs/tree/main/guidelines); when the two disagree, the guidelines win.

## Stack and commands

Python 3.12 notebooks in `notebooks/`, trained on Google Colab with a T4 GPU: Ultralytics 8.4.190 (YOLO11) on PyTorch, with pandas, matplotlib and Pillow for exploration. Ruff lints, and `scripts/check_repo.py` checks notebooks and tracked files with nbformat.

- `pip install -r requirements-dev.txt` installs the pinned dev tools.
- `ruff check .` lints notebooks and scripts with Ruff's default rules.
- `python scripts/check_repo.py` checks the repository; `--fix` clears notebook outputs in place.

CI runs both on every pull request. Training never runs in CI, since it needs a GPU and the 6 GB dataset.

## Notebooks

- One numbered notebook per stage: `01-yolo11-brick-detection.ipynb`, then `02-...` for part classification and so on. Add each to the README's notebook table with its Colab badge.
- Commit notebooks with outputs, execution counts and widget state cleared. Metrics and plots go in the PR's test evidence instead.
- The notebooks are written in Indonesian because they double as coursework; keep a notebook's language and naming consistent. The README and this file stay in English.
- Pin the libraries that change training results in the notebook's install cell, so every run trains the same way.
- Keep both paths working: Colab (data in `/content`, results on Google Drive) and local (everything next to the notebook).
- Run a changed notebook top to bottom before opening its PR. A smoke run on a small sample with few epochs is enough; say so in the test evidence, along with the config used.

## Data and weights

- Never commit datasets, training runs or weights: `data/`, `runs/`, `*.pt`, `*.onnx`, `*.zip`. `check_repo.py` fails when any are tracked.
- Notebooks download datasets from their source. Credit every dataset and its license in the README, e.g. CC BY 4.0 for *Tagged images with LEGO bricks*.
- Weights ship as GitHub Release assets tagged `vMAJOR.MINOR.PATCH`, never as a `release` branch (ADR-0005 in legoin-docs). Release notes list the training config and the test metrics: mAP@50, mAP@50-95, precision, recall and count MAE.
- Settings the backend must match, such as image size and the confidence threshold chosen on val, go in the release notes and in the PR's deployment section.

## Commits

Small and focused: one logical change, roughly 5 to 100 lines, explainable in one sentence and easy to revert. A notebook is one JSON file, so adding one can run longer; keep it to that notebook alone. Commit when a function, a fix or a logical step is done; if you pause work, you should be able to commit. Never mix a refactor with a feature, or a fix with formatting. No 1000+ line commits, no WIP commits on shared branches, and no vague messages like "update code" or "fix bugs".

**Before committing.** `ruff check .` and `python scripts/check_repo.py` pass, and a changed notebook runs top to bottom.

**Messages.** [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`, scope optional, e.g. `feat(detection): add YOLO11 brick detection notebook`. Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`. Mark breaking changes with `!`, e.g. `feat(detection)!: switch to a two-class model`.

## Branches

Trunk-based. `main` is always release-ready; there is no `develop`, `staging` or `release` branch. Work on short-lived branches named for the change: `feature/<short-description>`, `fix/<bug-description>` or `chore/<maintenance>`, e.g. `feature/part-classifier`. Every change reaches `main` through a pull request; commit directly to `main` only for an emergency hotfix.

## Pull requests

Start from an issue and agree on the approach before building. One problem per PR, ideally under 500 lines; split larger work into several PRs, stacked when they depend on each other.

- The title carries the ticket id, e.g. `feat(detection): add YOLO11 brick detection notebook (#2)`, and the PR links the issue.
- Fill in [the PR template](.github/pull_request_template.md): summary, problem, solution, test evidence, deployment prerequisites or breaking changes, notes.
- Test evidence for a notebook says where it ran (Colab T4, a server, a CPU smoke test), with which config, and what it produced.
- Call out anything the backend must change before deployment, such as new weights or a new threshold.

Merge only when CI passes, all discussions are resolved, required reviewers approve, and the commits follow the rules above. Squash-merge with the PR title as the commit subject.

## Docs

Keep the README sections current: overview, notebooks, dataset, tech stack, setup and run, checks, environment variables, model releases. Decisions are ADRs in [legoin-docs/decisions](https://github.com/al-dioooo/legoin-docs/tree/main/decisions), not in this repo.

## Secrets

Never commit `.env*` files, API keys, tokens (Hugging Face, Kaggle, Roboflow), credentials or logs. The notebooks need none today. If one ever does, read it from Colab secrets or an environment variable, and list it in the README.
