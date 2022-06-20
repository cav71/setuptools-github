import logging
from pathlib import Path
from typing import List, Optional

import pygit2  # type: ignore

from . import tools

log = logging.getLogger(__name__)


class Check:
    def __init__(
        self, msg: str, explain: Optional[str] = None, hint: Optional[str] = None
    ):
        self.msg = msg
        self.explain = explain
        self.hint = hint
        assert "\n" not in msg, f"only single line msg are allowed [{msg}]"


class Failure(Check):
    pass


def check_initfile(initfile: Path, _testmode: bool = False) -> Optional[List[Failure]]:
    """check the initfile presence and contents"""

    errors = []
    if _testmode or not initfile.exists():
        errors.append(Failure(f"no init file '{initfile}' found"))

    curver = tools.get_module_var(initfile, "__version__", abort=False)
    if _testmode or not curver:
        errors.append(
            Failure(
                f"cannot find __version__ in {initfile}",
                explain="""
        The initfile should contain the __version__ module level variable;
        it should be a text string in the MAJOR.MINOR.MICRO form.
        """,
            )
        )

    return errors if _testmode else errors[:1]


def check_in_master(
    repo: pygit2.Repository, master: Optional[str] = "master", _testmode: bool = False
) -> List[Failure]:
    """check we're in the master branch"""
    errors = []

    current = repo.head.shorthand
    log.debug("current branch %s (expecting %s)", current, master)

    if _testmode or current != master:
        errors.append(
            Failure(
                f"current branch is {current} not {master} branch",
            )
        )
    return errors if _testmode else errors[:1]


def check_clean(repo: pygit2.Repository, _testmode: bool = False):
    """check the current repo has not un-committed changes"""

    errors = []

    def ignore(f):
        return (f & pygit2.GIT_STATUS_WT_NEW) or (f & pygit2.GIT_STATUS_IGNORED)

    modified = {p for p, f in repo.status().items() if not ignore(f)}
    if _testmode or modified:
        errors.append(Failure("local modifications present (need to be committed)"))
    return errors if _testmode else errors[:1]


def check_has_single_remote(
    repo: pygit2.Repository, remote: Optional[str] = None, _testmode: bool = False
) -> List[Failure]:
    "given a pygit2 Repo instance check it has a single remote"

    errors = []
    # check repo has a single remote
    remotes = {remote.name for remote in repo.remotes}
    if _testmode or (len(remotes) > 1 and not remote):
        errors.append(
            Failure(
                f"multiple remotes defined: {', '.join(remotes)}",
                explain="""
    The workdir must have a single remote; use `git remote -v' to list all remotes
    and use the --remote flag to select one
    """,
            ),
        )

    if _testmode or (remote and remote not in remotes):
        errors.append(
            Failure(f"requested remote={remote} but found {', '.join(remotes)}")
        )
    return errors if _testmode else errors[:1]


# def check_for_release(
#     repo: pygit2.Repository,
#     initfile: Path,
#     curver: Optional[str] = None,
#     _testmode: bool = False,
# ) -> Optional[List[Failure]]:
#     from re import compile
#
#     regex_beta = compile(r"/?beta/(?P<ver>\d+([.]\d+)*)$")
#
#     errors = []
#
#     curver = curver or tools.get_module_var(initfile, "__version__", abort=False)
#
#     matched = regex_beta.match(repo.head.shorthand)
#     thisver = matched.groupdict()["ver"] if matched else None
#
#     # check we are in a beta branch
#     if _testmode or not regex_beta.match(repo.head.shorthand):
#         errors.append(
#             Failure(
#                 f"release should start from 'beta/{curver}' "
#                 f"branch (currently on {repo.head.shorthand})"
#             )
#         )
#
#     # check curver match the branch name
#     if _testmode or (thisver and thisver != curver):
#         errors.append(
#             Failure(
#                 f"current branch 'beta/{curver}' doesn't match "
#                 f"the initfile version {thisver}"
#             )
#         )
#
#     # check we aren't re-releasing
#     regex = compile("^refs/tags/")
#     tags = [r for r in repo.references if regex.match(r)]
#     if _testmode or (f"refs/tags/release/{curver}" in tags):
#         errors.append(Failure(f"tag release/{curver} present, cannot re-release"))
#
#     # check current branch is in sync with remote
#     # get all local and remote beta/ branches
#     # local_branches = {
#     #    b.rpartition("/")[2]: repo.lookup_branch(b)
#     #    for b in repo.branches.local
#     #    if regex_beta.search(b)
#     # }
#     remote_branches = {
#         b.rpartition("/")[2]: repo.lookup_branch(b, pygit2.GIT_BRANCH_REMOTE)
#         for b in repo.branches.remote
#         if regex_beta.search(b)
#     }
#
#     if _testmode or (
#         (curver in remote_branches)
#         and remote_branches[curver].target != repo.head.target
#     ):
#         target = remote_branches[curver].target if curver in remote_branches else None
#         errors.append(
#             Failure(
#                 f"local and remote branches beta/{curver} are out of sync",
#                 explain=f"""
#                 The local branch {repo.head.shorthand} has
#                 """
#                 f"""different hash from remote ({repo.head.target} != {target})
#                 """,
#             )
#         )
#
#     return errors if _testmode else errors[:1]
