import subprocess

import pytest
from setuptools_github import scm


def test_extract_beta_branches(git_project_factory):
    "test the branch and tag extraction function"
    from pygit2 import Repository

    # Create a repository with two beta branches tagged
    repo = git_project_factory("test_check_version-repo").create("0.0.0")
    repo.branch("beta/0.0.3")
    repo(["tag", "-m", "release", "release/0.0.3"])
    repo.branch("beta/0.0.4")
    repo(["tag", "-m", "release", "release/0.0.4"])
    repo(["checkout", "master"])
    assert (
        repo.dumps(mask=True)
        == f"""\
REPO: {repo.workdir}
 [status]
  On branch master
  nothing to commit, working tree clean

 [branch]
    beta/0.0.3 ABCDEFG [master] initial commit
    beta/0.0.4 ABCDEFG [master] initial commit
  * master     ABCDEFG initial commit

 [tags]
  release/0.0.3
  release/0.0.4

 [remote]

"""
    )

    repo1 = git_project_factory("test_check_version-repo1").create(clone=repo)
    repo1.branch("beta/0.0.2")
    assert (
        repo1.dumps(mask=True)
        == f"""\
REPO: {repo1.workdir}
 [status]
  On branch beta/0.0.2
  Your branch is up to date with 'master'.

  nothing to commit, working tree clean

 [branch]
  * beta/0.0.2                ABCDEFG [master] initial commit
    master                    ABCDEFG [origin/master] initial commit
    remotes/origin/HEAD       -> origin/master
    remotes/origin/beta/0.0.3 ABCDEFG initial commit
    remotes/origin/beta/0.0.4 ABCDEFG initial commit
    remotes/origin/master     ABCDEFG initial commit

 [tags]
  release/0.0.3
  release/0.0.4

 [remote]
  origin	{repo.workdir} (fetch)
  origin	{repo.workdir} (push)

"""
    )

    project = git_project_factory().create(clone=repo)
    project.branch("beta/0.0.1", "origin/master")
    # master branch is already present
    pytest.raises(
        subprocess.CalledProcessError, project.branch, "master", "origin/master"
    )

    project(["remote", "add", "repo1", repo1.workdir])
    project(["fetch", "--all"])

    assert (
        project.dumps(mask=True)
        == f"""\
REPO: {project.workdir}
 [status]
  On branch beta/0.0.1
  Your branch is up to date with 'origin/master'.

  nothing to commit, working tree clean

 [branch]
  * beta/0.0.1                ABCDEFG [origin/master] initial commit
    master                    ABCDEFG [origin/master] initial commit
    remotes/origin/HEAD       -> origin/master
    remotes/origin/beta/0.0.3 ABCDEFG initial commit
    remotes/origin/beta/0.0.4 ABCDEFG initial commit
    remotes/origin/master     ABCDEFG initial commit
    remotes/repo1/beta/0.0.2  ABCDEFG initial commit
    remotes/repo1/master      ABCDEFG initial commit

 [tags]
  release/0.0.3
  release/0.0.4

 [remote]
  origin	{repo.workdir} (fetch)
  origin	{repo.workdir} (push)
  repo1	{repo1.workdir} (fetch)
  repo1	{repo1.workdir} (push)

"""
    )
    local_branches, remote_branches, tags = [
        *project.branches(project.BETA_BRANCHES),
        project(["tag", "-l"]).split(),
    ]

    repo = Repository(project.workdir)
    assert (
        local_branches,
        remote_branches,
        tags,
    ) == scm.extract_beta_branches_and_release_tags(repo)

    assert local_branches == [
        "beta/0.0.1",
    ]
    assert remote_branches == {
        "origin": ["beta/0.0.3", "beta/0.0.4"],
        "repo1": ["beta/0.0.2"],
    }
    assert tags == ["release/0.0.3", "release/0.0.4"]
