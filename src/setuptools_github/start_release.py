import sys
import logging
from pathlib import Path
import re
from typing import List, Optional, Callable, Any

import pygit2  # type: ignore

from setuptools_github import tools, checks
from setuptools_github import checks as repo_checks


log = logging.getLogger(__name__)


class LocalFailure(Exception):
    def __int__(self, failures, *args, **kwargs):
        super().__init__(failures, *args, **kwargs)
        self.failures = failures


# def extract_beta_branches(branches: List[str], remote: Optional[str] = None):
#     result = set()
#     for branch in branches:
#         match = branch.partition("/")[0]
#         if remote and remote != match:
#             continue
#         if re.search(r"beta/\d+([.]\d+)*", branch):
#             result.add(branch)
#     return result
#
#
# # TODO
# def checks_for_beta(
#     repo: pygit2.Repository, curver: str, initfile: Path, _testmode: bool = False
# ):
#     print(">" * 40)
#     pass
#
#
# def _checks_for_beta(
#     repo: pygit2.Repository,
#     remote: Optional[str],
#     error: Callable[[str], Any],
#     dryrun: bool,
#     force: bool,
#     curver: str,
#     mode: str,
# ):
#     # check we are on master
#     current = repo.head.shorthand
#     log.debug("current branch %s", current)
#     if current != "master":
#         (log.error if dryrun else error)(  # type: ignore
#             f"current branch is '{current}' but this script runs on the 'master' branch"
#         )
#
#     # check we have no uncommitted changes
#     def ignore(f):
#         return (f & pygit2.GIT_STATUS_WT_NEW) or (f & pygit2.GIT_STATUS_IGNORED)
#
#     modified = {p for p, f in repo.status().items() if not ignore(f)}
#     if modified:
#         (log.error if (dryrun or force) else error)(  # type: ignore
#             "local modification staged for commit, use -f|--force to skip check"
#         )
#
#     # check the current version has a beta/<curver> branch
#     remote_branches = extract_beta_branches(repo.branches.remote, remote=remote)
#     local_branches = extract_beta_branches(repo.branches.local)
#
#     if not any(remote_branches | local_branches):
#         # no beta/X.Y.Z branches, we start fresh
#         return curver
#
#     is_in_local = bool([b for b in local_branches if b.endswith(f"beta/{curver}")])
#     is_in_remote = bool([b for b in remote_branches if b.endswith(f"beta/{curver}")])
#     if not (is_in_local or is_in_remote):
#         (log.error if (dryrun or force) else error)(  # type: ignore
#             f"cannot find 'beta/{curver}' branch in the local or remote branches"
#         )
#
#     newver = bump_version(curver, mode)
#     is_in_local = bool([b for b in local_branches if b.endswith(f"beta/{newver}")])
#     is_in_remote = bool([b for b in remote_branches if b.endswith(f"beta/{newver}")])
#     if is_in_local:
#         (log.error if (dryrun or force) else error)(  # type: ignore
#             f"found 'beta/{newver}' branch in the local branches"
#         )
#     if is_in_remote:
#         (log.error if (dryrun or force) else error)(  # type: ignore
#             f"found 'beta/{newver}' branch in the remote branches"
#         )
#
#     return newver


def beta(repo, curver, mode, initfile, workdir, master, remote, force, dryrun, error):
    # various checks and generate the new version / branch name
    newver = bump_version(curver, mode)
    print("&&&&&", newver)
    return

    # newver = checks_for_beta(repo, remote, error, dryrun, force, curver, mode)
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
    repo,
    curver,
    mode,
    initfile,
    workdir,
    master,
    remote,
    force,
    dryrun,
    error,
    **kwargs,
):
    return

    #    #   1. curver is not either in local and remote
    #    if curver not in (set(local_branches) | set(remote_branches)):
    #        error(
    #            f"current project has version {curver} but there aren't"
    #            f" any beta/{curver} branch local or remote",
    #            explain=f"""
    #        Try to first create a beta/{curver} using:
    #           {sys.argv[0]} micro {initfile}
    #        """,
    #        )
    #    #   2. curver is in remote and local branches
    #    elif curver in (set(local_branches) & set(remote_branches)):
    #        lref = repo.lookup_reference(local_branches[curver].name)
    #        rref = repo.lookup_reference(remote_branches[curver].name)
    #        if lref.target != rref.target:
    #            error("local and remote branches 'branch/{curver}' are out of sync",
    #                explain=f"""
    #                Please pull the {remote_branches[curver].name} into {local_branches[curver].name}
    #                """)
    #        ref = lref
    #        # check the two branches are in sync or bail out
    #        raise RuntimeError("NOT DONE YET")
    #    #   3. curver is in remote only
    #    elif curver not in local_branches:
    #        # TODO create local branch from remote
    #        raise RuntimeError("NOT DONE YET")
    #        ref = repo.lookup_reference(repo.lookup_branch(remote_branches[curver]))
    #        repo.checkout(ref)
    #    #   4. curver is local only
    #    elif curver not in remote_branches:
    #        # check master is in sync with local branch (unless is --force)
    #        ref = repo.lookup_reference(repo.lookup_branch(local_branches[curver]).name)
    #        mref = repo.lookup_reference(repo.lookup_branch("master").name)
    #        if not force and (ref.target != mref.target):
    #            error(
    #                f"local '{local_branches[curver]}' is not in sync with master",
    #                explain="""
    #            Either you need to pull master into '{local_branches[curver]}' or
    #            (if it is ok) you can use the --force flag.:
    #            """,
    #            )
    repo.checkout(ref)
    repo.references.create(f"refs/tags/release/{curver}", ref.target)


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
    parser.add_argument("--master", help="use the branch as 'master'", default="master")
    parser.add_argument("--remote", help="use remote")

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

    def error(message, explain=""):
        out = parser.format_usage().split("\n")
        out.append(f"{parser.prog}: {message}")
        if explain:
            out.extend(tools.indent(explain.rstrip()).split("\n"))
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

    for d in ["verbose"]:
        delattr(options, d)
    return options.__dict__


def run(
    mode,
    initfile,
    workdir,
    master,
    force,
    dryrun,
    error,
    remote,
    _testmode=False,
    _dont_exit=False,
):
    workdir = workdir.resolve()
    log.debug("using working dir %s", workdir)

    # get the Repository instance on workdir
    repo = pygit2.Repository(workdir)

    checks = []
    try:
        # we need an initfile
        failures = repo_checks.check_initfile(initfile) or []
        checks.extend(failures)
        if checks:
            raise LocalFailure(checks)

        # we start always in master
        failures = repo_checks.check_in_master(repo, master) or []
        checks.extend(failures)
        if checks:
            raise LocalFailure(checks)

        # check if we have local modififcations
        failures = repo_checks.check_clean(repo) or []
        checks.extend(failures)
        if checks:
            raise LocalFailure(checks)

        # check if we have one single remote (or we default
        failures = repo_checks.check_has_single_remote(repo, remote) or []
        checks.extend(failures)
        if checks:
            raise LocalFailure(checks)

        # get the current version from initfile
        curver = tools.get_module_var(initfile, "__version__", abort=False)
        log.info("current version [%s]", curver)

        if mode == "release":
            checks.extend(checks_for_release(repo, curver, initfile, _testmode) or [])
        else:
            checks.extend(checks_for_beta(repo, curver, initfile, _testmode) or [])
    except LocalFailure:
        if _dont_exit:
            return checks
        for failure in checks:
            print(f"* {failure.msg}")
            if failure.explain:
                print(tools.indent(failure.explain[1:], pre="  | "))
        exit(2)

    return (release if mode == "release" else beta)(
        repo, curver, mode, initfile, workdir, master, remote, force, dryrun, error
    )


if __name__ == "__main__":
    run(**parse_args())
