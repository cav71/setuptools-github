from argparse import Namespace
from setuptools_github import script


class MyError(Exception):
    pass


def errorfn(message, explain="", hint=""):
    raise MyError(message, explain, hint)


def test_add_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    script.add_arguments(parser)
    assert len(parser._actions) == 5  # all action + help action


def test_process_options(tmp_path, git_project_factory):
    options = Namespace(workdir=tmp_path)
    try:
        script.process_options(options, error=errorfn)
    except MyError as e:
        assert e.args[0] == "no git directory"

    repo = git_project_factory().create(force=True, nobranch=True)
    options = Namespace(workdir=repo.workdir)
    try:
        script.process_options(options, error=errorfn)  # , error=error)
    except MyError as e:
        assert e.args[0] == "invalid git repository"


def test_main_make_beta(git_project_factory):
    repo = git_project_factory().create(force=True)

    options = Namespace(
        initfile=repo.workdir / "src" / "__init__.py",
        repo=repo,
        mode="make-beta",
        error=errorfn,
        master=None
    )
    try:
        script.main.__wrapped__(options)
    except MyError as exc:
        assert exc.args[0].startswith("cannot find version file")

    repo = git_project_factory().create(version="0.0.0")
    options = Namespace(
        initfile=repo.workdir / "src" / "__init__.py",
        repo=repo,
        mode="make-beta",
        error=errorfn,
        master="master"
    )
    script.main.__wrapped__(options)
    assert set(repo.branches.local) == {"master", "beta/0.0.0"}

    try:
        script.main.__wrapped__(options)
    except MyError as exc:
        assert exc.args[0].startswith("branch 'beta/0.0.0' already present")


def test_main_make_release(git_project_factory):

    repo = git_project_factory().create(version="0.0.0")
    old = repo.branch("beta/0.0.0", "master")
    repo(["checkout", old])

    options = Namespace(
        initfile=repo.workdir / "src" / "__init__.py",
        repo=repo,
        mode="micro",
        error=errorfn,
        master="master"
    )
    try:
        script.main.__wrapped__(options)
    except MyError as exc:
        assert exc.args[0].startswith("wrong branch 'master'")

    assert set(repo.branches.local) == {"master", "beta/0.0.0"}
    repo(["checkout", "beta/0.0.0"])

    try:
        script.main.__wrapped__(options)
    except MyError as exc:
        assert exc.args[0].startswith("branch 'beta/0.0.0' already present")
