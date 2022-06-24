import argparse
import sys
import logging
from pathlib import Path
import functools
import re
from typing import List, Optional, Tuple, Dict, Any

import pygit2  # type: ignore

from setuptools_github import tools
from setuptools_github import checks


log = logging.getLogger(__name__)


def parse_args(args: Optional[str] = None, testmode: bool = False) -> Dict[str, Any]:
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


def extract_beta_branches(
    repo: pygit2.Repository,
) -> Tuple[List[str], Dict[str, List[str]], List[str]]:
    """given a pygit2 Repository object extracts local and remote beta branches

     This function will extract all the 'beta' branches (eg. with the beta/N(.N)* form)
     and the release tags (eg. with release/N(.N)* form) from it.

    Examples:
         >>> extract_beta_branches(pygit2.Repository(.. some path))
         (
             ['beta/0.0.1', 'beta/0.0.4'],
             {'origin': ['beta/0.0.3', 'beta/0.0.4'], 'repo1': ['beta/0.0.2']},
             ['release/0.0.3', 'release/0.0.4']
         )
    """
    tagre = re.compile(r"^refs/tags/release/")
    local_branches = []
    remote_branches: Dict[str, List[str]] = {}
    for name in repo.branches.local:
        if checks.BETAEXPR.search(name):
            local_branches.append(name)

    for name in repo.branches.remote:
        if checks.BETAEXPR.search(name):
            origin, _, name = name.partition("/")
            if origin not in remote_branches:
                remote_branches[origin] = []
            remote_branches[origin].append(name)

    pre = len("refs/tags/")
    tags = [name[pre:] for name in repo.references if tagre.search(name)]
    return local_branches, remote_branches, tags


def beta(
    repo: pygit2.Repository,
    curver: str,
    mode: str,
    initfile: Path,
    workdir: Path,
    dryrun: bool,
    error: checks.ErrorFunctionType,
) -> None:
    newver = tools.bump_version(curver or "", mode)
    log.info("beta release %s -> %s", curver, newver)

    local_branches, remote_branches, tags = extract_beta_branches(repo)

    # it's the first branch, we won't bump the version
    if not (local_branches or remote_branches):
        newver = curver
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

    # log.info("switching to new branch '%s'%s", newbranch, " (skip)" if dryrun else "")
    if not dryrun:
        commit = repo.revparse_single(repo.head.shorthand)
        repo.branches.local.create(newbranch, commit)
        ref = repo.lookup_reference(repo.lookup_branch(newbranch).name)
        repo.checkout(ref)


def release(
    repo: pygit2.Repository,
    curver: str,
    mode: str,
    initfile: Path,
    workdir: Path,
    dryrun: bool,
    error: checks.ErrorFunctionType,
) -> None:
    log.info("releasing %s", curver)

    local_branches, remote_branches, tags = extract_beta_branches(repo)

    ref = None
    if f"beta/{curver}" in local_branches:
        ref = repo.lookup_reference(f"refs/heads/beta/{curver}")
    else:
        # TODO check local and remote branches aren't out of sync
        for origin, branches in remote_branches.items():
            if f"beta/{curver}" not in branches:
                continue

            ref = repo.lookup_reference(f"refs/remotes/{origin}/beta/{curver}")
            break

    if not ref:
        error(
            "cannot find a suitable branc/ref",
            """cannot find a reference for beta/{curver}
              """,
        )
    elif not dryrun:
        repo.checkout(ref)
        repo.references.create(f"refs/tags/release/{curver}", ref.target)


def run(mode, initfile, workdir, dryrun, error, master):
    workdir = workdir.resolve()
    log.debug("using working dir %s", workdir)

    # get the Repository instance on workdir
    repo = pygit2.Repository(workdir)
    try:
        branch = repo.head.shorthand
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

    # get all the beta branches
    # check the current version has a beta/<curver> branch

    # TODO check for local modifications
    checks.check_repo_mods(error, workdir, initfile)
    checks.check_initfile(error, initfile)
    checks.check_branch(error, mode, branch, master)

    # TODO check for branch matching init file
    local_branches, remote_branches, tags = extract_beta_branches(repo)
    checks.check_version(
        error, mode, initfile, branch, local_branches, remote_branches, tags, branch
    )

    curver = tools.get_module_var(initfile, "__version__", abort=False)
    log.info("current version [%s]", curver)
    return (release if mode == "release" else beta)(
        repo, curver, mode, initfile, workdir, dryrun, error
    )

    return

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
        repo, curver, mode, initfile, workdir, dryrun, error
    )


if __name__ == "__main__":
    run(**parse_args())
