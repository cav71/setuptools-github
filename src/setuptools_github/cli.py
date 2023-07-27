from __future__ import annotations

import argparse
import functools
import logging
import sys
from typing import Any, Callable, Protocol

from . import tools


class ErrorFn(Protocol):
    def __call__(self, message: str, explain: str | None, hint: str | None) -> None:
        ...


class AbortExecutionError(Exception):
    @staticmethod
    def _strip(txt):
        txt = txt or ""
        txt = txt[1:] if txt.startswith("\n") else txt
        txt = tools.indent(txt, pre="")
        return txt[:-1] if txt.endswith("\n") else txt

    def __init__(
        self,
        message: str,
        explain: str | None = None,
        hint: str | None = None,
        usage: str | None = None,
    ):
        self.message = message.strip()
        self.explain = explain
        self.hint = hint
        self.usage = usage

    def __str__(self):
        out = []
        if self.usage:
            out.extend(self.usage.strip().split("\n"))
        if self.message:
            out.extend(self._strip(self.message).split("\n"))
        if self.explain:
            out.append("reason:")
            out.extend(tools.indent(self.explain).split("\n"))
        if self.hint:
            out.append("hint:")
            out.extend(tools.indent(self.hint).split("\n"))
        return "\n".join((line.strip() if not line.strip() else line) for line in out)


def _add_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    """parses args from the command line

    Args:
        args: command line arguments or None to pull from sys.argv
        doc: text to use in cli description
    """
    parser.add_argument("-n", "--dry-run", dest="dryrun", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")


def _process_options(
    options: argparse.Namespace, errorfn: ErrorFn
) -> argparse.Namespace | None:
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
    return options


def cli(
    add_arguments: Callable[[argparse.ArgumentParser], None] | None = None,
    process_options: Callable[[argparse.Namespace, ErrorFn], argparse.Namespace | None]
    | None = None,
    doc: str | None = None,
):
    @functools.wraps(cli)
    def _fn(main: Callable[[argparse.Namespace], Any]):
        @functools.wraps(main)
        def _fn1(args: None | list[str] = None) -> Any:
            try:

                class ParserFormatter(
                    argparse.ArgumentDefaultsHelpFormatter,
                    argparse.RawDescriptionHelpFormatter,
                ):
                    pass

                description, _, epilog = (doc or "").partition("\n")
                parser = argparse.ArgumentParser(
                    formatter_class=ParserFormatter,
                    description=description,
                    epilog=epilog,
                )
                _add_arguments(parser)
                if add_arguments:
                    add_arguments(parser)

                options = parser.parse_args(args=args)

                def error(
                    message: str,
                    explain: str = "",
                    hint: str = "",
                    usage: str | None = None,
                ):
                    raise AbortExecutionError(message, explain, hint, usage)

                errorfn: ErrorFn = functools.partial(error, usage=parser.format_usage())
                options.error = errorfn

                options = _process_options(options, errorfn) or options
                if process_options:
                    options = process_options(options, errorfn) or options

                return main(options)
            except AbortExecutionError as err:
                print(str(err), file=sys.stderr)  # noqa: T201
                raise SystemExit(2) from None
            except Exception:
                raise

        return _fn1

    return _fn
