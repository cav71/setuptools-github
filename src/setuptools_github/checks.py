from typing import List, Optional

import pygit2  # type: ignore


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
