"""create a beta branch or release a beta branch

This script will either create a new beta branch:

     setuptools-github beta ./src/setuptools_github/__init__.py

Or will release the beta branch and will move inot the next minor

    setuptools-github {major|minor|micro|make-beta} ./src/setuptools_github/__init__.py

"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from . import cli, scm, tools

log = logging.getLogger(__name__)


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--master", help="the 'master' branch")
    parser.add_argument(
        "-w",
        "--workdir",
        help="git working dir",
        default=Path("."),
        type=Path,
    )
    parser.add_argument("mode", choices=["micro", "minor", "major", "make-beta"])
    parser.add_argument("initfile", metavar="__init__.py", type=Path)


def process_options(
    options: argparse.Namespace, error: cli.ErrorFn
) -> argparse.Namespace:
    try:
        options.repo = repo = scm.GitRepo(options.workdir)
        repo.status()
    except scm.GitError:
        error(
            "no git directory",
            "It looks the repository is not a git repo",
            hint="init the git directory",
        )
    log.info("working dir set to '%s'", options.workdir)
    try:
        branch = repo.head.shorthand
        log.info("current branch set to '%s'", branch)
    except scm.GitError:
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
    # master branch
    master = options.master or (
        options.repo.config["init.defaultbranch"]
        if "init.defaultbranch" in options.repo.config
        else "master"
    )

    if options.repo.status(untracked_files="no", ignored=False):
        options.error(f"modified files in {options.repo.workdir}")
    if not options.initfile.exists():
        options.error(f"cannot find version file {options.initfile}")

    version = tools.get_module_var(options.initfile, "__version__")
    log.info("got version %s for branch '%s'", version, options.repo.head.shorthand)
    if not version:
        raise tools.InvalidVersionError(f"cannot find a version in {options.initfile}")

    # fetching all remotes
    options.repo(["fetch", "--all"])

    if options.mode == "make-beta":
        if options.repo.head.name != f"refs/heads/{master}":
            options.error(
                f"wrong branch '{options.repo.head.name}', expected '{master}'"
            )

        for branch in [*options.repo.branches.local, *options.repo.branches.remote]:
            if not branch.endswith(f"beta/{version}"):
                continue
            options.error(f"branch '{branch}' already present")
        log.info("creating branch '%s'", f"/beta/{version}")
        options.repo.branch(f"beta/{version}", master)
        options.repo(["checkout", master])
    elif options.mode in {"micro", "minor", "major"}:
        # we need to be in the beta/N.M.O branch
        expr = re.compile(r"refs/heads/beta/(?P<beta>\d+([.]\d+)*)$")
        if not (match := expr.search(options.repo.head.name)):
            options.error(
                f"wrong branch '{options.repo.head.shorthand}'",
                f"expected to be in 'beta/{version}' branch",
                f"git checkout beta/{version}",
            )
            return
        local = match.group("beta")
        if local != version:
            options.error(f"wrong version file {version=} != {local}")

        # tag
        options.repo(["tag", "-a", f"release/{version}", "-m", f"released {version}"])

        # switch to master
        options.repo(["checkout", master])

        # bump version
        new_version = tools.bump_version(version, options.mode)
        tools.set_module_var(options.initfile, "__version__", new_version)

        # commit
        options.repo.commit(
            options.initfile, f"version bump {version} -> {new_version}"
        )

        print(  # noqa: T201
            tools.indent(
                f"""
        The release is almost complete.

        To proceed:
            git push origin release/{version}

        To rever this script:
            git reset --hard HEAD~1
            git tag -d release/{version}
        """
            ),
            file=sys.stderr,
        )
    else:
        options.error(f"unsupported mode {options.mode=}")
        raise RuntimeError(f"unsupported mode {options.mode=}")


if __name__ == "__main__":
    main()
