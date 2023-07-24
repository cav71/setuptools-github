"""create a beta branch or release a beta branch

This script will either create a new beta branch:

     setuptools-github beta ./src/setuptools_github/__init__.py

Or will release the beta branch and will move inot the next minor

    setuptools-github {major|minor|micro} ./src/setuptools_github/__init__.py

"""
from __future__ import annotations
import logging
import re
from pathlib import Path
import argparse
from . import cli, tools
import pygit2  # type: ignore


log = logging.getLogger(__name__)


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--master", default="master", help="the 'master' branch")
    parser.add_argument(
        "-w",
        "--workdir",
        help="git working dir",
        default=Path("."),
        type=Path,
    )
    parser.add_argument("initfile", metavar="__init__.py", type=Path)
    parser.add_argument("mode", choices=["micro", "minor", "major", "make-beta"])


def process_options(
    options: argparse.Namespace, error: cli.ErrorFn
) -> argparse.Namespace:
    try:
        options.repo = repo = pygit2.Repository(options.workdir)
    except pygit2.GitError:
        error(
            "no git directory",
            "It looks the repository is not a git repo",
            hint="init the git directory",
        )
    log.info("working dir set to '%s'", options.workdir)
    try:
        branch = repo.head.shorthand
        log.info("current branch set to '%s'", branch)
    except pygit2.GitError:
        error(
            "invalid git repository",
            """
              It looks the repository doesn't have any branch,
              you should:
                git checkout --orphan <branch-name>
              """,
            hint="create a git branch",
        )
    return options


@cli.cli(add_arguments, process_options, __doc__)
def main(options) -> None:
    if options.repo.status(untracked_files="no", ignored=False):
        options.error(f"modified files in {options.repo.workdir}")
    if not options.initfile.exists():
        options.error(f"cannot find version file {options.initfile}")

    version = tools.get_module_var(options.initfile, "__version__")

    if options.mode == "make-beta":
        if options.repo.head.name != f"refs/heads/{options.master}":
            options.error(
                f"wrong branch '{options.repo.head.name}', expected '{options.master}'"
            )

        log.info("got version %s", version)
        for branch in options.repo.branches.local:
            if not branch.endswith(f"beta/{version}"):
                continue
            options.error(f"branch '{branch}' already present")
        log.info("creating branch '%s'", f"/beta/{version}")
        commit = options.repo.revparse_single("HEAD")
        options.repo.branches.local.create(f"/beta/{version}", commit)
    elif options.mode in {"micro", "minor", "major"}:
        # we need to be in the beta/N.M.O branch
        expr = re.compile(r"refs/heads/beta/(?P<beta>\d+([.]\d+)*$")
        if not (match := expr.search(options.repo.head.name)):
            options.error(
                f"wrong branch '{options.repo.head.name}'"
                f"expected 'refs/heads/beta/{version}'"
            )
            return
        local = match.group("beta")
        if local != version:
            options.error(f"wrong version file {version=} != {local}")
        # TODO
        #  1. tag
        #  2. switch to master
        #  3. bump version
        #  4. commit
    else:
        options.error(f"unsupported mode {options.mode=}")
        raise RuntimeError(f"unsupported mode {options.mode=}")


if __name__ == "__main__":
    main()
