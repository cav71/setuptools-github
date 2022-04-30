import pytest

from setuptools_github import start_release as sr


def test_indent():
    found = sr.indent(
        """
    This is a simply
       indented text
      with some special
         feature
"""[
            1:
        ],
        "..",
    )
    assert (
        """
..This is a simply
..   indented text
..  with some special
..     feature
"""[
            1:-1
        ]
        == found.strip()
    )


def test_bump_version():
    assert "0.0.2" == sr.bump_version("0.0.1", "micro")
    assert "0.0.3" == sr.bump_version("0.0.2", "micro")
    assert "0.1.0" == sr.bump_version("0.0.2", "minor")
    assert "2.0.0" == sr.bump_version("1.2.3", "major")


def test_check_remotes(git_project_factory):
    project = git_project_factory("remotes-project").create("0.0.3")

    assert not sr.check_remotes(project.repo)

    # we force a new remote
    project.repo.remotes.create("remote-name", "url")
    assert "remote-name" == sr.check_remotes(project.repo)

    project.repo.remotes.create("another-remote-name", "url")
    pytest.raises(RuntimeError, sr.check_remotes, project.repo)

    pytest.raises(RuntimeError, sr.check_remotes, project.repo, remote="blah")
    assert "remote-name" == sr.check_remotes(project.repo, remote="remote-name")


def test_extract_beta_branches():
    branches = [
        "master",
        "main",
        "beta/0.0.0",
        "foobar/beta/0.0.1",
        "foobar/beta/0.0.0.2",
        "beta/gamma/0.0",
    ]

    assert sr.extract_beta_branches(branches) == {
        "beta/0.0.0",
        "foobar/beta/0.0.1",
        "foobar/beta/0.0.0.2",
    }
    assert sr.extract_beta_branches(branches, remote="foobar") == {
        "foobar/beta/0.0.1",
        "foobar/beta/0.0.0.2",
    }


def test_end2end_betas(git_project_factory, capsys):
    "end2end run for a beta branch"

    project = git_project_factory("beta-project").create("0.0.3")
    assert project.branch == "master"
    assert project.version == "0.0.3"

    # create the first beta branch:
    #  we checkout the beta/0.0.3 branch
    #  the version stays the same as master
    args = [
        "-w",
        project.workdir,
        "minor",
        project.initfile,
        "--no-checks",
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    sr.run(**kwargs)
    assert project.branch == "beta/0.0.3"
    assert project.version == "0.0.3"
    return

    # make sure we cannot re-apply in a non-master branch
    pytest.raises(SystemExit, sr.run, **kwargs)
    project.checkout("master")

    # second round to create a beta branch
    #  we update the __init__.py to 0.1.0 (minor) in master
    assert project.branch == "master"
    assert project.version == "0.0.3"

    sr.run(**kwargs)
    assert project.branch == "beta/0.1.0"
    assert project.version == "0.1.0"

    # verify master branch has the version matching the beta
    project.checkout("master")
    assert project.branch == "master"
    assert project.version == "0.1.0"


def test_end2end_release(git_project_factory, capsys):
    "end2end run for a release"
    project = git_project_factory("projectXX").create("0.1.0")
    assert project.branch == "master"
    assert project.version == "0.1.0"

    # we try to release from master, without first going through a beta first
    # -> we fail
    args = [
        "-w",
        project.workdir,
        "release",
        project.initfile,
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    pytest.raises(SystemExit, sr.run, **kwargs)

    # creating the beta
    args = [
        "-w",
        project.workdir,
        "minor",
        project.initfile,
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    sr.run(**kwargs)
    assert project.branch == "beta/0.1.0"
    assert project.version == "0.1.0"

    # try to release on the non master branch (and fail again)
    args = [
        "-w",
        project.workdir,
        "release",
        project.initfile,
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    pytest.raises(SystemExit, sr.run, **kwargs)
    assert project.branch == "beta/0.1.0"
    assert project.version == "0.1.0"

    project.checkout("master")
    args = [
        "-w",
        project.workdir,
        "release",
        project.initfile,
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    sr.run(**kwargs)
    assert project.branch == "beta/0.1.0"
    assert project.version == "0.1.0"
