"""The command line. One verb, so `[project.scripts]` has something to register."""

import argparse
from collections.abc import Sequence

from newpkg import __version__
from newpkg.core import greet


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line.

    Parameters
    ----------
    argv
        Arguments to parse. `None` reads `sys.argv`.

    Returns
    -------
    int
        The process exit code.
    """
    parser = argparse.ArgumentParser(prog="newpkg", description="The placeholder command.")
    parser.add_argument("--version", action="version", version=__version__)
    verbs = parser.add_subparsers(dest="verb", required=True)
    hello = verbs.add_parser("greet", help="Print a greeting.")
    hello.add_argument("name", nargs="?", default="world", help="Who to greet.")

    args = parser.parse_args(argv)
    print(greet(args.name))
    return 0
