from __future__ import annotations
import re
import pygit2

from . import checks


def extract_beta_branches(
    repo: pygit2.Repository,
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """given a pygit2 Repository object extracts local and remote beta branches

     This function will extract all the 'beta' branches (eg. with the beta/N(.N)* form)
     and the release tags (eg. with release/N(.N)* form) from it.

    Examples:
         >>> extract_beta_branches(pygit2.Repository(.. some path))
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
