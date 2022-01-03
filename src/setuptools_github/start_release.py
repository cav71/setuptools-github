import pathlib
import logging

import pygit2  # type: ignore

from . import tools


log = logging.getLogger(__name__)


def newversion(version, mode):
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


def repo_checks(repo, error, dryrun, force, curver, newbranch):
    # check repo has a single remote
    remotes = {remote.name for remote in repo.remotes}
    if len(remotes) != 1:
        error(f"multiple remotes defined: {', '.join(remotes)}")
    remote = remotes.pop()

    # check the current version has a beta/<curver> branch
    branche_names = set(
        r.partition("/")[2] if r.partition("/")[0] == remote else r
        for r in repo.branches
    )
    if f"beta/{curver}" not in branche_names:
        (log.warning if (dryrun or force) else error)(
            f"there's no 'beta/{curver}' branch in the worktree or in {remote}"
        )

    # check we are on master
    current = repo.head.shorthand
    log.debug("current branch %s", current)
    if current != "master":
        (log.warning if dryrun else error)(
            f"current branch is [{current}] but must be master branch"
        )

    # check we have no uncommitted changes
    def ignore(f):
        return (f & pygit2.GIT_STATUS_WT_NEW) or (f & pygit2.GIT_STATUS_IGNORED)

    modified = {p for p, f in repo.status().items() if not ignore(f)}
    if modified:
        (log.warning if (dryrun or force) else error)(
            "local modification staged for commit, use -f|--force to skip check"
        )

    # check we haven't already branched
    if newbranch in branche_names:
        (log.warning if dryrun else error)(
            f"new branch {newbranch} fund in current branche set"
        )


def parse_args(args=None):
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

    parser.add_argument(
        "-w",
        "--workdir",
        help="git working dir",
        default=pathlib.Path("."),
        type=pathlib.Path,
    )
    parser.add_argument("mode", choices=["micro", "minor", "major"])
    parser.add_argument("initfile", metavar="__init__.py")

    options = parser.parse_args(args)

    options.error = parser.error
    logging.basicConfig(level=logging.DEBUG if options.verbose else logging.INFO)
    for d in ["verbose"]:
        delattr(options, d)
    return options.__dict__


def run(mode, initfile, workdir, force, dryrun, error):
    workdir = workdir.resolve()
    log.debug("using working dir %s", workdir)

    # get the current version from initfile
    curver = tools.set_module_var(initfile, "__version__", None)[0]
    if not curver:
        error(f"cannot find __version__ in {initfile}")
    log.info("current version '%s'", curver)

    # generate the new version / branch name
    newver = newversion(curver, mode)
    newbranch = f"beta/{newver}"
    log.info("creating new version %s -> %s (branch %s)", curver, newver, newbranch)

    # repo
    repo = pygit2.Repository(workdir)

    # various checks
    repo_checks(repo, error, dryrun, force, curver, newbranch)

    # modify the __init__
    log.info("updating init file %s%s", initfile, " (skip)" if dryrun else "")
    if not dryrun:
        tools.set_module_var(initfile, "__version__", newver)

    msg = f"beta release {newver}"
    log.info("committing '%s'%s", msg, " (skip)" if dryrun else "")
    if not dryrun:
        refname = repo.head.name
        author = repo.default_signature
        commiter = repo.default_signature
        parent = repo.revparse_single(repo.head.shorthand).hex
        repo.index.add(initfile)
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


def main():
    return run(**parse_args())


if __name__ == "__main__":
    main()
