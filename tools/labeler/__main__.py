"""python -m tools.labeler <command>: see the README's "Labeling your own photos"."""

import argparse
from pathlib import Path

from .files import DEFAULT_ROOT, Layout


def main(argv: list[str] | None = None) -> None:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT,
        help="the data root, data/foto_mandiri of notebooks 02 and 03 (default: %(default)s)",
    )
    parser = argparse.ArgumentParser(
        prog="python -m tools.labeler", description="Label the team's phone photos of bricks."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    cut = commands.add_parser(
        "cut", parents=[common], help="cut stage 1 crops from photos/<session>/*"
    )
    cut.add_argument(
        "--models", type=Path,
        help="where release files are kept (default: a models folder next to the root)",
    )

    label = commands.add_parser(
        "label", parents=[common], help="label the crops on a local page, as one labeler"
    )
    label.add_argument("--port", type=int, default=8765, help="(default: %(default)s)")
    label.add_argument("--no-browser", action="store_true", help="don't open the page")

    args = parser.parse_args(argv)
    layout = Layout(args.root.resolve())
    if args.command == "cut":
        from .cut import cut as run_cut  # loads Ultralytics, which only `cut` needs

        run_cut(layout, (args.models or layout.root.parent / "models").resolve())
    elif args.command == "label":
        from .label import serve

        serve(layout, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
