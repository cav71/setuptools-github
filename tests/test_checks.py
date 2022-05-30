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
