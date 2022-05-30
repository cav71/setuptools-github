import setuptools_github.checks as sr


def test_check_has_single_remote(git_project_factory):
    "check the repo has a single remote"
    project = git_project_factory("remotes-project").create("0.0.3")

    # this will dump all detectable issues at once
    assert len(sr.check_has_single_remote(project.repo, _testmode=True)) == 2

    # check we start with no remote -> no failure
    assert not sr.check_has_single_remote(project.repo)

    # we force a new remote -> still no failure
    project.create_branch("origin/remote-name", remote="invalid-url")
    assert not sr.check_has_single_remote(project.repo)

    # if we ask for a non-exhistant remote we fail
    assert sr.check_has_single_remote(project.repo, "origin/remote-name2")

    # adding a second remote
    project.create_branch("origin/remote-name2", remote="another-url")
    assert sr.check_has_single_remote(project.repo)

    # we can explicitly use a remote to refer to (this won't trigger an error)
    assert not sr.check_has_single_remote(project.repo, "origin/remote-name2")


def test_check_initifile(git_project_factory):
    "checks initfile presence and contents"

    # we create a project without an initfile
    project = git_project_factory("check-initfile").create(None)

    # this will dump all issues at once
    assert len(sr.check_initfile(project.initfile, _testmode=True)) == 2

    # initfile not present -> fail
    assert sr.check_initfile(project.initfile)
    assert sr.check_initfile(project.initfile)[0].msg.startswith("no file")

    project.initfile.parent.mkdir(parents=True, exist_ok=True)

    # touching the file (but still failing because of the missing __version__ variable)
    project.initfile.write_text("")
    assert sr.check_initfile(project.initfile)[0].msg.startswith(
        "cannot find __version__ in"
    )

    # we succeed on well formed initfile
    project.initfile.write_text("__version__ = '1.2.3'")
    assert not sr.check_initfile(project.initfile)
