import re
import sys
from pathlib import Path
from typing import List, Optional, Callable, Dict
import argparse

from . import tools

BETAEXPR = re.compile(r"beta/(?P<ver>\d+([.]\d+)*)")


def error(
    message: str,
    explain="",
    hint="",
    parser: Optional[argparse.ArgumentParser] = None,
    _testmode: bool = False,
) -> None:
    out = parser.format_usage().split("\n")
    out.append(f"{parser.prog}: {message}")
    if explain:
        out.extend(tools.indent(explain.rstrip()).split("\n"))

    if _testmode:
        raise tools.AbortExecution(message, explain, hint)
    else:
        print("\n".join(out), file=sys.stderr)
        raise SystemExit(2)


def check_initfile(error: Callable[[str, str, str], None], initfile: Path) -> None:
    if initfile.exists():
        curver = tools.get_module_var(initfile, "__version__", abort=False)
        if not curver:
            error(
                "init file has an invalid __version__ module variable",
                explain="""
              An init file (eg. __init__.py) should be defined containing
              a __version__ = "<major>.<minor>.<micro>" version
              """,
                hint=f"add a __version__ module variable in '{initfile}'",
            )
    else:
        error(
            "no init file found",
            explain="""
              An init file (eg. __init__.py) should be defined containing
              a __version__ = "<major>.<minor>.<micro>" version
              """,
            hint=f"add an init file in '{initfile}'",
        )


def check_branch(
    error: Callable[[str, str, str], None],
    mode: str,
    curbranch: str,
    master: str = "master",
):
    # curbranch == repo.head.shorthand
    if mode in {"release"}:
        match = BETAEXPR.search(curbranch)
        if not match:
            error(
                f"{mode} starts from a beta/N.M.O branch",
                f"""
                A {mode} starts from a beta/N.M.O branch, not from '{curbranch}'
                """,
                hint="switch to a beta/N.M.O branch",
            )
    elif mode in {"major", "minor", "micro"}:
        # betas start from the 'master' branch
        if curbranch != master:
            error(
                f"'{mode}' starts from '{master}' branch",
                f"""
                While generating a branch for '{mode}' we assume as starting
                branch to be '{master}' but we are in '{curbranch}'.
                """,
                hint=f"""
                Switch to the '{master}' branch or pass the --master flag
                """,
            )
    else:
        raise RuntimeError(f"invalid {mode}")


def check_version(
    error: Callable[[str, str, str], None],
    mode: str,
    initfile: Path,
    local_branches: List[str],
    remote_branches: Dict[str, List[str]],
    tags: List[str],
    master: str,
):
    curver = tools.get_module_var(initfile, "__version__", abort=False)
    nextver = tools.bump_version(curver, mode)

    if mode in {"release"}:
        if f"release/{curver}" in tags:
            error(
                "release already prsent",
                f"""
                A release 'release/{curver}' tag is present for the current branch
                """,
                hint="""
                check the __version__ is correct
                """,
            )
    else:
        if f"beta/{nextver}" in local_branches:
            error(
                f"next version branch 'beta/{nextver}' already present"
                " in local branches",
                f"""
                when creating a new branch 'beta/{nextver}' a local branch
                with that name has been found already
                """,
                hint=f"""
                change the version from '{curver}' in the '{master}' branch initfile
                """,
            )
        for origin, branches in remote_branches.items():
            if f"beta/{nextver}" in branches:
                error(
                    f"next version branch 'beta/{nextver}' already present in"
                    " remote branches",
                    f"""
                when creating a new branch 'beta/{nextver}' a remote branch with
                that name has been found already in '{origin}'
                """,
                    hint=f"""
                make sure the '{curver}' in the initfile in '{master}' branch is correct
                """,
                )
