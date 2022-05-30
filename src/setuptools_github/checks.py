from pathlib import Path
from typing import List, Optional

import pygit2  # type: ignore

from . import tools


class Check:
    def __init__(self, msg: str, explain: Optional[str] = None):
        self.msg = msg
        self.explain = explain


class Failure(Check):
    pass


def check_has_single_remote(
    repo: pygit2.Repository, remote: Optional[str] = None, _testmode: bool = False
) -> Optional[List[Check]]:
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


def check_initfile(initfile: Path, _testmode: bool = False) -> Optional[List[Check]]:
    "check the initfile presence and contents"

    errors = []
    if _testmode or not initfile.exists():
        errors.append(Failure(f"no file '{initfile}' found"))

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
