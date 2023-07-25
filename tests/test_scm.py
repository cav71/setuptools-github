import subprocess

import pytest

from setuptools_github import scm


def test_lookup(git_project_factory):
    repo = git_project_factory().create("0.0.0")
    dstdir = repo.workdir / "a" / "b" / "c"
    dstdir.mkdir(parents=True)
    (dstdir / "out.txt").touch()
    assert (dstdir / "out.txt").exists()

    assert str(scm.lookup(dstdir).workdir) == f"{repo.workdir}"


def test_handle_remote_and_local_repos(git_project_factory):
    "test branch handling across repos"

    def check_branches(repo):
        srepo = scm.GitRepo(repo.workdir)
        assert set(repo.branches.local) == set(srepo.branches.local)
        assert set(repo.branches.remote) == set(srepo.branches.remote)

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
    check_branches(repo)

    # Clone from repo and adds a new branch
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
    check_branches(repo1)

    # Clone from repo, adds a new branch and adds repo1 as remote
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
    check_branches(project)

    repox = scm.GitRepo(project.workdir)
    assert project.dumps() == repox.dumps()
