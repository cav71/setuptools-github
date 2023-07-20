def test_operation_create(git_project_factory):
    # simple git repo (only 1 .keep file and 1 .git dir)
    repo0 = git_project_factory().create()
    assert set(f.name for f in repo0.workdir.glob("*")) == {".git"}

    # another repo with a "version" src/__init__.py file
    repo1 = git_project_factory().create("0.0.0")
    assert set(f.name for f in repo1.workdir.glob("*")) == {".git", "src"}

    # make sure they aren't the same
    assert repo0.workdir != repo1.workdir
    assert repo0.gitdir != repo1.gitdir

    # cloning
    repo2 = git_project_factory().create(clone=repo0)
    assert repo2.workdir != repo0.workdir
    assert repo2.gitdir != repo0.gitdir
    assert set(f.name for f in repo2.workdir.glob("*")) == {".git"}

    repo3 = git_project_factory().create(clone=repo1)
    assert repo3.workdir != repo1.workdir
    assert repo3.gitdir != repo1.gitdir
    assert set(f.name for f in repo3.workdir.glob("*")) == {".git", "src"}


def test_operation_dump(git_project_factory):
    repo = git_project_factory().create()
    assert set(f.name for f in repo.workdir.glob("*")) == {".git"}

    assert (
        repo.dumps(mask=True)
        == f"""\
REPO: {repo.workdir}
 [status]
  On branch master
  nothing to commit, working tree clean

 [branch]
  * master ABCDEFG initial

 [tags]

 [remote]

"""
    )


def test_operation_clone(git_project_factory):
    repo = git_project_factory().create()
    assert repo(["config", "user.name"]).strip() == "First Last"
    assert repo(["config", "user.email"]).strip() == "user@email"

    repo1 = git_project_factory().create(clone=repo)
    assert repo1(["config", "user.name"]).strip() == "First Last"
    assert repo1(["config", "user.email"]).strip() == "user@email"
