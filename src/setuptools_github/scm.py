from __future__ import annotations
import re
from pathlib import Path
import pygit2

from . import checks


def lookup(path: Path) -> pygit2.Repository | None:
    cur = path
    found = False
    while not found:
        if (cur / ".git").exists():
            return pygit2.Repository(cur)
        if str(cur) == cur.root:
            break
        cur = cur.parent
    return None


def extract_beta_branches_and_release_tags(
    repo: pygit2.Repository,
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """extracts the beta branches (local and remotes) and release tags

     This function will extract all the 'beta' branches (eg. with the beta/N(.N)* form)
     and the release tags (eg. with release/N(.N)* form) from it.

    Examples:
         >>> extract_beta_branches_and_release_tags(pygit2.Repository(.. some path))
         (
             ['beta/0.0.1', 'beta/0.0.4'],  # local branches
             {'origin': ['beta/0.0.3', 'beta/0.0.4'], 'repo1': ['beta/0.0.2']},
             ['release/0.0.3', 'release/0.0.4']
         )
    """
    tagre = re.compile(r"^refs/tags/release/")
    local_branches = []
    remote_branches: dict[str, list[str]] = {}
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
