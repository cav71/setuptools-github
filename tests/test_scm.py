import subprocess

import pytest

try:
    import pygit2
except ImportError:
    pygit2 = None

from setuptools_github import scm


@pytest.mark.skipif(not pygit2, reason="pygit2 not installed")
def test_scm_pygit2_equivalence_status(git_project_factory):
    repo = git_project_factory().create("0.0.0")

    # add a new untracked file
    (repo.workdir / "untracked.txt").write_text("A")

    # add two new tracked and committed files
    (repo.workdir / ".gitignore").write_text("ignored.txt\n")
    (repo.workdir / "modified.txt").write_text("B")
    (repo.workdir / "unchanged.txt").write_text("C")
    (repo.workdir / "deleted.txt").write_text("D")

    repo.commit(
        [
            repo.workdir / ".gitignore",
            repo.workdir / "modified.txt",
            repo.workdir / "unchanged.txt",
            repo.workdir / "deleted.txt",
        ],
        "initial",
    )

    (repo.workdir / "ignored.txt").write_text("E")
    (repo.workdir / "modified.txt").write_text("xxx")
    (repo.workdir / "deleted.txt").unlink()

    srepo = scm.GitRepo(repo.workdir)
    grepo = pygit2.Repository(repo.workdir)

    assert repo.status() == srepo.status()
    for untracked_files in ["all", "no"]:
        assert srepo.status(untracked_files=untracked_files) == grepo.status(
            untracked_files=untracked_files
        )


def test_lookup(git_project_factory):
    repo = git_project_factory().create("0.0.0")
    dstdir = repo.workdir / "a" / "b" / "c"
    dstdir.mkdir(parents=True)
    (dstdir / "out.txt").touch()
    assert (dstdir / "out.txt").exists()

    assert str(scm.lookup(dstdir).workdir) == f"{repo.workdir}"


@pytest.mark.skipif(not pygit2, reason="pygit2 not installed")
def test_extract_beta_branches(git_project_factory):
    "test the branch and tag extraction function"

    def check_branches(repo):
        srepo = scm.GitRepo(repo.workdir)
        grepo = pygit2.Repository(repo.workdir)
        assert set(repo.branches.local) == set(srepo.branches.local)
        assert set(srepo.branches.local) == set(grepo.branches.local)
        assert set(repo.branches.remote) == set(srepo.branches.remote)
        assert set(srepo.branches.remote) == set(grepo.branches.remote)

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
