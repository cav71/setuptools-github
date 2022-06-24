import argparse
import sys
import logging
import functools
import re
from typing import List, Optional, Tuple, Dict

import pygit2  # type: ignore

from setuptools_github import tools
from setuptools_github import checks


log = logging.getLogger(__name__)


def error(
    message: str,
    explain: str = "",
    hint: str = "",
    parser: Optional[argparse.ArgumentParser] = None,
    testmode: bool = False,
):
    if parser:
        out = parser.format_usage().split("\n")
        out.append(f"{parser.prog}: {message}")
    if explain:
        out.extend(tools.indent(explain.rstrip()).split("\n"))

    if testmode:
        raise tools.AbortExecution(message, explain, hint)
    else:
        print("\n".join(out), file=sys.stderr)
        raise SystemExit(2)


def parse_args(args: Optional[str] = None, testmode: bool = False):
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

    parser = argparse.ArgumentParser(formatter_class=F, description=__doc__)

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

    # options.checks = not options.no_checks

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


# def check_remotes(
#     repo: pygit2.Repository,
#     dryrun: bool = False,
#     remote: Optional[str] = None,
#     error: Optional[Callable[[str], Any]] = None,
# ):
#     "given a pygit2 Repo instance check it has a single remote"
#
#     if not error:
#
#         def errorfn(msg):
#             raise RuntimeError(msg)
#
#         error = errorfn
#
#     # check repo has a single remote
#     remotes = {remote.name for remote in repo.remotes}
#     if len(remotes) > 1 and not remote:
#         (log.error if dryrun else error)(
#             f"multiple remotes defined: {', '.join(remotes)}"
#         )
#     if remote and remote not in remotes:
#         error(f"requested remote={remote} but found {', '.join(remotes)}")
#         (log.error if dryrun else error)(
#             f"user select remote={remote} but only found {', '.join(remotes)}"
#         )
#     remote = remote or (remotes or [None]).pop()
#     log.debug("current remote '%s'", remote)
#     return remote
#
#
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


# def repo_checks(
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
#             f"current branch is '{current}' but this
#             script runs on the 'master' branch"
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
#     newver = "123"  # bump_version(curver, mode)
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


def beta(repo, curver, mode, initfile, workdir, dryrun, error):

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
    #
    # return newbranch


def release(repo, curver, mode, initfile, workdir, dryrun, error):
    log.info("releasing %s", curver)

    local_branches, remote_branches, tags = extract_beta_branches(repo)

    ref = repo.lookup_reference(repo.lookup_branch(local_branches[curver]).name)
    raise RuntimeError(f"xxx {type(ref)} / {ref}")
    pass

    #
    # # check we aren't regenerating a tag
    # regex = re.compile("^refs/tags/")
    # tags = [r for r in repo.references if regex.match(r)]
    # if f"refs/tags/release/{curver}" in tags:
    #     error(f"there's already a {curver} tag refs/tags/release/{curver}")
    #
    # local_branches = {
    #     b.rpartition("/")[2]: b for b in repo.branches.local if b == f"beta/{curver}"
    # }
    # remote_branches = {
    #     b.rpartition("/")[2]: b
    #     for b in repo.branches.remote
    #     if b.endswith(f"/beta/{curver}")
    # }
    #
    # # 4 cases
    # #   1. curver is not either in local and remote
    # if curver not in (set(local_branches) | set(remote_branches)):
    #     error(
    #         f"ncurrent project has version {curver} but there aren't"
    #         f" any beta/{curver} branch local or remote",
    #         explain="""
    #     Tried to create a release for {curver} but no beta/{curver} branch
    #     has not beeing found.
    #     """,
    #     )
    # #   2. curver is in remote and local branches
    # elif curver in (set(local_branches) & set(remote_branches)):
    #     # check the two branches are in sync or bail out
    #     raise RuntimeError("NOT DONE YET")
    # #   3. curver is in remote only
    # elif curver not in local_branches:
    #     # TODO create local branch from remote
    #     raise RuntimeError("NOT DONE YET")
    #     ref = repo.lookup_reference(repo.lookup_branch(remote_branches[curver]))
    #     repo.checkout(ref)
    # #   4. curver is local only
    # elif curver not in remote_branches:
    #     # check master is in sync with local branch (unless is --force)
    #     ref = repo.lookup_reference(repo.lookup_branch(local_branches[curver]).name)
    #     mref = repo.lookup_reference(repo.lookup_branch("master").name)
    #     if not force and (ref.target != mref.target):
    #         error(
    #             f"local '{local_branches[curver]}' is not in sync with master",
    #             explain="""
    #         Either you need to pull master into '{local_branches[curver]}' or
    #         (if it is ok) you can use the --force flag.:
    #         """,
    #         )
    # repo.checkout(ref)
    # repo.references.create(f"refs/tags/release/{curver}", ref.target)


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
