import re
from pathlib import Path
from typing import Callable, Dict, List, TypeVar

from mypy_extensions import Arg, DefaultArg

from . import tools

BETAEXPR = re.compile(r"beta/(?P<ver>\d+([.]\d+)*)")

ErrorFunctionType = TypeVar(
    "ErrorFunctionType",
    bound=Callable[
        [
            Arg(str, "message"),  # noqa: undefined-name
            DefaultArg(str, "explain"),  # noqa: undefined-name
            DefaultArg(str, "hint"),  # noqa: undefined-name
        ],
        None,
    ],
)


def check_repo_mods(error: ErrorFunctionType, workdir: Path, initfile: Path):
    from pygit2 import GIT_STATUS_IGNORED, GIT_STATUS_WT_NEW, Repository  # type: ignore

    repo = Repository(workdir)

    rel_initfile = str(initfile.absolute().relative_to(workdir.absolute())).replace(
        "\\", "/"
    )
    unstracked = {p for p, f in repo.status().items() if f & GIT_STATUS_WT_NEW}
    if rel_initfile in unstracked:
        error(
            "init file is not tracked",
            explain="""
                  An init file (eg. __init__.py) should be defined containing
                  a __version__ = "<major>.<minor>.<micro>" version
                  """,
            hint=f"create and git add an init file in '{initfile}'",
        )

    def ignore(f):
        return (f & GIT_STATUS_WT_NEW) or (f & GIT_STATUS_IGNORED)

    modified = {p for p, f in repo.status().items() if not ignore(f)}
    if rel_initfile in modified:
        error(
            "init file has local modifications",
            explain="""
                  An init file (eg. __init__.py) should be git tracked and not modified
                  """,
            hint=f"git revert or commit init file changes in '{initfile}'",
        )


def check_initfile(error: ErrorFunctionType, initfile: Path) -> None:
    if not initfile.exists():
        error(
            "no init file found",
            explain="""
                  An init file (eg. __init__.py) should be defined containing
                  a __version__ = "<major>.<minor>.<micro>" version
                  """,
            hint=f"add an init file in '{initfile}'",
        )
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


def check_branch(
    error: ErrorFunctionType,
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
    error: ErrorFunctionType,
    mode: str,
    initfile: Path,
    branch: str,
    local_branches: List[str],
    remote_branches: Dict[str, List[str]],
    tags: List[str],
    master: str,
):
    curver = tools.get_module_var(initfile, "__version__", abort=False)
    nextver = tools.bump_version(curver or "", mode)

    if mode in {"release"}:
        if branch != f"beta/{curver}":
            error(
                f"wrong version '{curver}' from initfile",
                f"""
                The current branch '{branch}' has a version '{curver}' in
                the initfile '{initfile}'.
                """,
                hint="""
                fix the __version__ variable in the initfile
                """,
            )

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
