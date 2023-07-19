import io


def test_git_repo_create(git_project_factory):
    # simple git repo (only 1 .keep file and 1 .git dir)
    repo0 = git_project_factory().create()
    assert set(f.name for f in repo0.workdir.glob("*")) == {".git", ".keep"}

    # another repo with a "version" src/__init__.py file
    repo1 = git_project_factory().create("0.0.0")
    assert set(f.name for f in repo1.workdir.glob("*")) == {".git", ".keep", "src"}

    # make sure they aren't the same
    assert repo0.workdir != repo1.workdir
    assert repo0.gitdir != repo1.gitdir

    # cloning
    repo2 = git_project_factory().create(clone=repo0)
    assert repo2.workdir != repo0.workdir
    assert repo2.gitdir != repo0.gitdir
    assert set(f.name for f in repo2.workdir.glob("*")) == {".git", ".keep"}

    repo3 = git_project_factory().create(clone=repo1)
    assert repo3.workdir != repo1.workdir
    assert repo3.gitdir != repo1.gitdir
    assert set(f.name for f in repo3.workdir.glob("*")) == {".git", ".keep", "src"}


def test_git_repo_dump(git_project_factory):
    from re import sub

    repo = git_project_factory().create()
    assert set(f.name for f in repo.workdir.glob("*")) == {".git", ".keep"}

    buf = io.StringIO()
    repo.dump(buf)
    found = sub(r"master [a-zA-Z0-9]{7} initial", "master XXXXXXX initial",
                buf.getvalue())
    assert found == f"""\
REPO: {repo.workdir}
 [status]
  On branch master
  nothing to commit, working tree clean

 [branch]
  * master XXXXXXX initial

 [tags]

 [remote]

"""
