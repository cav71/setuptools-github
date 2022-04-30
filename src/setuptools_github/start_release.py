import sys
import logging
import functools
import re
from typing import List, Optional, Callable, Any

import pygit2  # type: ignore

from setuptools_github import tools


log = logging.getLogger(__name__)


def indent(txt: str, pre: str = " " * 2) -> str:
    "simple text indentation"

    from textwrap import dedent

    txt = dedent(txt)
    if txt.endswith("\n"):
        last_eol = "\n"
        txt = txt[:-1]
    else:
        last_eol = ""

    return pre + txt.replace("\n", "\n" + pre) + last_eol


def bump_version(version: str, mode: str) -> str:
    """given a version string will bump accordying to mode

    Eg.
        bump_version("1.0.3", "micro")
        -> "1.0.4"
        bump_version("1.0.3", "minor")
        -> "1.1.0"
    """
    newver = [int(n) for n in version.split(".")]
    if mode == "major":
        newver[-3] += 1
        newver[-2] = 0
        newver[-1] = 0
    elif mode == "minor":
        newver[-2] += 1
        newver[-1] = 0
    else:
        newver[-1] += 1
    return ".".join(str(v) for v in newver)


def check_remotes(
    repo: pygit2.Repository,
    dryrun: bool = False,
    remote: Optional[str] = None,
    error: Optional[Callable[[str], Any]] = None,
):
    "given a pygit2 Repo instance check it has a single remote"

    if not error:

        def error(msg):
            raise RuntimeError(msg)

    # check repo has a single remote
    remotes = {remote.name for remote in repo.remotes}
    if len(remotes) > 1 and not remote:
        (log.error if dryrun else error)(
            f"multiple remotes defined: {', '.join(remotes)}"
        )
    if remote and remote not in remotes:
        error(f"requested remote={remote} but found {', '.join(remotes)}")
        (log.error if dryrun else error)(
            f"user select remote={remote} but only found {', '.join(remotes)}"
        )
    remote = remote or (remotes or [None]).pop()
    log.debug("current remote '%s'", remote)
    return remote


def extract_beta_branches(branches: List[str], remote: Optional[str] = None):
    result = set()
    for branch in branches:
        match = branch.partition("/")[0]
        if remote and remote != match:
            continue
        if re.search(r"beta/\d+([.]\d+)*", branch):
            result.add(branch)
    return result


def repo_checks(
    repo: pygit2.Repository,
    remote: Optional[str],
    error: Callable[[str], Any],
    dryrun: bool,
    force: bool,
    curver: str,
    mode: str,
):
    # check we are on master
    current = repo.head.shorthand
    log.debug("current branch %s", current)
    if current != "master":
        (log.error if dryrun else error)(
            f"current branch is '{current}' but this script runs on the 'master' branch"
        )

    # check we have no uncommitted changes
    def ignore(f):
        return (f & pygit2.GIT_STATUS_WT_NEW) or (f & pygit2.GIT_STATUS_IGNORED)

    modified = {p for p, f in repo.status().items() if not ignore(f)}
    if modified:
        (log.error if (dryrun or force) else error)(
            "local modification staged for commit, use -f|--force to skip check"
        )

    # check the current version has a beta/<curver> branch
    remote_branches = extract_beta_branches(repo.branches.remote, remote=remote)
    local_branches = extract_beta_branches(repo.branches.local)

    if not any(remote_branches | local_branches):
        # no beta/X.Y.Z branches, we start fresh
        return curver

    is_in_local = bool([b for b in local_branches if b.endswith(f"beta/{curver}")])
    is_in_remote = bool([b for b in remote_branches if b.endswith(f"beta/{curver}")])
    if not (is_in_local or is_in_remote):
        (log.error if (dryrun or force) else error)(
            f"cannot find 'beta/{curver}' branch in the local or remote branches"
        )

    newver = bump_version(curver, mode)
    is_in_local = bool([b for b in local_branches if b.endswith(f"beta/{newver}")])
    is_in_remote = bool([b for b in remote_branches if b.endswith(f"beta/{newver}")])
    if is_in_local:
        (log.error if (dryrun or force) else error)(
            f"found 'beta/{newver}' branch in the local branches"
        )
    if is_in_remote:
        (log.error if (dryrun or force) else error)(
            f"found 'beta/{newver}' branch in the remote branches"
        )

    return newver


def parse_args(args=None):
    from pathlib import Path
    from argparse import (
        ArgumentParser,
        ArgumentDefaultsHelpFormatter,
        RawDescriptionHelpFormatter,
    )

    class F(ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter):
        pass

    parser = ArgumentParser(formatter_class=F, description=__doc__)

    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("-n", "--dry-run", dest="dryrun", action="store_true")
    parser.add_argument("--remote", help="use remote")
    parser.add_argument("--no-checks", action="store_true")

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

    options.checks = not options.no_checks

    def error(message, explain=""):
        out = parser.format_usage().split("\n")
        out.append(f"{parser.prog}: {message}")
        if explain:
            out.extend(indent(explain.rstrip()).split("\n"))
        print("\n".join(out), file=sys.stderr)

        class S(SystemExit):
            pass

        s = S(2)
        s.out = "\n".join(out)
        raise S(2)

    options.error = error

    logging.basicConfig(
        format="%(levelname)s:%(name)s:(dry-run) %(message)s"
        if options.dryrun
        else "%(levelname)s:%(name)s:%(message)s",
        level=logging.DEBUG if options.verbose else logging.INFO,
    )

    for d in ["verbose", "no_checks"]:
        delattr(options, d)
    return options.__dict__


def beta(repo, curver, mode, initfile, workdir, force, dryrun, error, checks, remote):
    # various checks and generate the new version / branch name
    newver = repo_checks(repo, remote, error, dryrun, force, curver, mode)
    newbranch = f"beta/{newver}"
    if newver == curver:
        log.info(
            "creating first version branch '%s' (v. %s) from 'master'",
            newbranch,
            newver,
        )
    else:
        log.info(
            "creating new version branch '%s' (v. %s) from 'master' (%s)",
            newbranch,
            newver,
            curver,
        )

    # modify the __init__
    log.info("updating init file %s (%s -> %s)", initfile, curver, newver)
    if not dryrun:
        tools.set_module_var(initfile, "__version__", newver)

    # commit the updated __init__.py in the master branch
    msg = f"beta release {newver}"
    log.info("committing '%s'%s", msg, " (skip)" if dryrun else "")
    if not dryrun:
        refname = repo.head.name
        author = repo.default_signature
        commiter = repo.default_signature
        parent = repo.revparse_single(repo.head.shorthand).hex
        relpath = initfile.absolute().relative_to(workdir)
        repo.index.add(str(relpath).replace("\\", "/"))
        repo.index.write()
        tree = repo.index.write_tree()
        oid = repo.create_commit(refname, author, commiter, msg, tree, [parent])
        log.info("created oid %s", oid)

    log.info("switching to new branch '%s'%s", newbranch, " (skip)" if dryrun else "")
    if not dryrun:
        commit = repo.revparse_single(repo.head.shorthand)
        repo.branches.local.create(newbranch, commit)
        ref = repo.lookup_reference(repo.lookup_branch(newbranch).name)
        repo.checkout(ref)

    return newbranch


def release(
    repo, curver, mode, initfile, workdir, force, dryrun, error, checks, remote
):

    # check we aren't regenerating a tag
    regex = re.compile("^refs/tags/")
    tags = [r for r in repo.references if regex.match(r)]
    if f"refs/tags/release/{curver}" in tags:
        error(f"there's already a {curver} tag refs/tags/release/{curver}")

    local_branches = {
        b.rpartition("/")[2]: b for b in repo.branches.local if b == f"beta/{curver}"
    }
    remote_branches = {
        b.rpartition("/")[2]: b
        for b in repo.branches.remote
        if b.endswith(f"/beta/{curver}")
    }

    # 4 cases
    #   1. curver is not either in local and remote
    if curver not in (set(local_branches) | set(remote_branches)):
        error(
            f"ncurrent project has version {curver} but there aren't"
            f" any beta/{curver} branch local or remote",
            explain="""
        Tried to create a release for {curver} but no beta/{curver} branch
        has not beeing found.
        """,
        )
    #   2. curver is in remote and local branches
    elif curver in (set(local_branches) & set(remote_branches)):
        # check the two branches are in sync or bail out
        raise RuntimeError("NOT DONE YET")
    #   3. curver is in remote only
    elif curver not in local_branches:
        # TODO create local branch from remote
        raise RuntimeError("NOT DONE YET")
        ref = repo.lookup_reference(repo.lookup_branch(remote_branches[curver]))
        repo.checkout(ref)
    #   4. curver is local only
    elif curver not in remote_branches:
        # check master is in sync with local branch (unless is --force)
        ref = repo.lookup_reference(repo.lookup_branch(local_branches[curver]).name)
        mref = repo.lookup_reference(repo.lookup_branch("master").name)
        if not force and (ref.target != mref.target):
            error(
                f"local '{local_branches[curver]}' is not in sync with master",
                explain="""
            Either you need to pull master into '{local_branches[curver]}' or
            (if it is ok) you can use the --force flag.:
            """,
            )
    repo.checkout(ref)
    repo.references.create(f"refs/tags/release/{curver}", ref.target)


def run(mode, initfile, workdir, force, dryrun, error, checks, remote):
    workdir = workdir.resolve()
    log.debug("using working dir %s", workdir)

    # get the Repository instance on workdir
    repo = pygit2.Repository(workdir)

    # we need an initfile
    if not initfile.exists():
        error(f"no file '{initfile}' found")

    # check we are on master
    if repo.head.shorthand not in {"master", "main"}:
        error(
            "current branch is '{repo.head.shorthand}' but"
            " this script runs on the 'master' branch"
        )

    # check we have a single remote or use the remote passed in --remote flag
    remote = check_remotes(
        repo,
        dryrun,
        remote,
        error=functools.partial(
            error,
            explain="""
    The workdir must have a single remote; use `git remote -v' to list all remotes
    and use the --remote flag to select one
    """,
        ),
    )
    log.info("remote [%s]", remote)

    # get the current version from initfile
    curver = tools.get_module_var(initfile, "__version__", abort=False)
    if not curver:
        error(
            f"cannot find __version__ in {initfile}",
            explain="""
        The initfile should contain the __version__ module level variable;
        it should be a text string in the MAJOR.MINOR.MICRO form.
        """,
        )
    log.info("current version [%s]", curver)

    return (release if mode == "release" else beta)(
        repo, curver, mode, initfile, workdir, force, dryrun, error, checks, remote
    )


if __name__ == "__main__":
    run(**parse_args())
