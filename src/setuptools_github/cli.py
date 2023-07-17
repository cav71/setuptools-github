from __future__ import annotations
import sys
import argparse
import logging
import functools
from typing import Any

from . import tools


def parse_args(args: str | None = None, testmode: bool = False) -> dict[str, Any]:
    """parses args from the command line

    Args:
        args: command line arguments or None to pull from sys.argv
        testmode: internal flag, if set will not SystemExit but will
                  raises tools.AbortExecution
    """
    from pathlib import Path

    class F(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
    ):
        pass

    parser = argparse.ArgumentParser(
        formatter_class=F, description=__doc__, prog="AAAA"
    )

    parser.add_argument("-n", "--dry-run", dest="dryrun", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--master", default="master", help="the 'master' branch")

    # parser.add_argument("-f", "--force", action="store_true")
    # parser.add_argument("--no-checks", action="store_true")

    parser.add_argument(
        "-w",
        "--workdir",
        help="git working dir",
        default=Path("."),
        type=Path,
    )
    parser.add_argument("mode", choices=["micro", "minor", "major", "release"])
    parser.add_argument("initfile", metavar="__init__.py", type=Path)

    options = parser.parse_args(args)

    def error(message, explain="", hint="", parser=None, testmode=False):
        out = []
        if parser:
            out.extend(tools.indent(parser.format_usage()).split("\n"))
        if message:
            out.extend(tools.indent(message).split("\n"))
        if explain:
            out.append("reason:")
            out.extend(tools.indent(explain).split("\n"))
        if hint:
            out.append("hint:")
            out.extend(tools.indent(hint).split("\n"))

        if testmode:
            raise tools.AbortExecution(message, explain, hint)
        else:
            print()
            print("\n".join(out), file=sys.stderr)
            raise SystemExit(2)

    options.error = functools.partial(error, parser=parser, testmode=testmode)

    logging.basicConfig(
        format="%(levelname)s:%(name)s:(dry-run) %(message)s"
        if options.dryrun
        else "%(levelname)s:%(name)s:%(message)s",
        level=logging.DEBUG if options.verbose else logging.INFO,
    )

    for d in [
        "verbose",
    ]:
        delattr(options, d)
    return options.__dict__
