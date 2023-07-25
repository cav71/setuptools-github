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
    parser.add_argument("--master", help="the 'master' branch")
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
    assert version
    log.info("got version %s for branch '{options.repo.head.name}'", version)

    # fetching all remotes
    [remote.fetch() for remote in options.repo.remotes]

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
        commit = options.repo.revparse_single("HEAD")
        options.repo.branches.local.create(f"/beta/{version}", commit)
    elif options.mode in {"micro", "minor", "major"}:
        # we need to be in the beta/N.M.O branch
        expr = re.compile(r"refs/heads/beta/(?P<beta>\d+([.]\d+)*)$")
        if not (match := expr.search(options.repo.head.name)):
            options.error(
                f"wrong branch '{options.repo.head.name}' "
                f"expected 'refs/heads/beta/{version}'"
            )
            return
        local = match.group("beta")
        if local != version:
            options.error(f"wrong version file {version=} != {local}")

        # tag
        obj = options.repo.get(options.repo.head.target)
        options.repo.create_tag(
            f"release/{version}",
            obj.oid,
            pygit2.GIT_OBJ_COMMIT,
            obj.author,
            f"release {version}",
        )

        # switch to master
        branch = options.repo.lookup_branch(master)
        head = options.repo.lookup_reference(branch.name)
        options.repo.checkout(head.name)

        # bump version
        tools.set_module_var(
            options.initfile, "__version__", tools.bump_version(version, options.mode)
        )

        # commit
        ref = options.repo.head.name
        parents = [options.repo.head.target]
        obj = options.repo.get(options.repo.head.target)
        index = options.repo.index
        index.add(
            str(options.initfile.relative_to(options.repo.workdir)).replace("\\", "/")
        )
        index.write()
        tree = index.write_tree()
        options.repo.create_commit(
            ref, obj.author, obj.author, "release", tree, parents
        )

    else:
        options.error(f"unsupported mode {options.mode=}")
        raise RuntimeError(f"unsupported mode {options.mode=}")


if __name__ == "__main__":
    main()
