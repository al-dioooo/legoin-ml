# legoin-ml

The models behind Legoin: notebooks that train and evaluate them, and the weights the backend will serve. Product docs, team guidelines and decisions live in [legoin-docs](https://github.com/al-dioooo/legoin-docs); the web app is [legoin-web](https://github.com/al-dioooo/legoin-web).

A Legoin scan runs in stages:

1. **Detection** finds every brick in one photo with YOLO11 and a single `lego` class. The box count is the first inventory.
2. **Part classification** names each cropped brick. Planned.
3. **Color** reads each brick's color from its crop. Planned.

## Checks

```bash
pip install -r requirements-dev.txt
ruff check .
python scripts/check_repo.py
```

`check_repo.py` fails when a notebook is invalid or still holds outputs, or when data or weights are in the repository. `python scripts/check_repo.py --fix` clears notebook outputs in place. CI runs both commands on every pull request.

## Environment variables

None. The notebooks need no keys or tokens.

## Contributing

Follow the [legoin-docs guidelines](https://github.com/al-dioooo/legoin-docs/tree/main/guidelines): work on a branch, write Conventional Commits, and merge through a pull request linked to an issue. Clear notebook outputs before committing.
