"""create a beta branch or release a beta branch

This script will either create a new beta branch:

     setuptools-github beta ./src/setuptools_github/__init__.py

Or will release the beta branch and will move inot the next minor

    setuptools-github {major|minor|micro} ./src/setuptools_github/__init__.py

"""
from __future__ import annotations
import logging
from pathlib import Path
import argparse
from . import cli, tools
import pygit2


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
    options.repo = repo = pygit2.Repository(options.workdir)
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
    if options.mode == "make-beta":
        if options.repo.status(untracked_files="no", ignored=False):
            options.error(f"modified files in {options.repo.workdir}")
        version = tools.get_module_var(options.initfile, "__version__")
        log.info("got version %s", version)
        for branch in options.repo.branches:
            if not branch.endswith(f"/beta/{version}"):
                continue
            options.error(f"branch '{branch}' already present")
        log.info("creating branch '%s'", f"/beta/{version}")
        commit = options.repo.revparse_single("HEAD")
        options.repo.branches.local.create(f"/beta/{version}", commit)
        options.repo.branches.local.delete(f"/beta/{version}")
    else:
        options.error(f"unsupported mode {options.mode=}")
        raise RuntimeError(f"unsupported mode {options.mode=}")


if __name__ == "__main__":
    main()
