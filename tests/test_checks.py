from setuptools_github import checks, tools


def test_check_has_single_remote(git_project_factory):
    "check the repo has a single remote"
    project = git_project_factory("remotes-project").create("0.0.3", remote=False)

    # this will dump all detectable issues at once
    assert len(checks.check_has_single_remote(project.repo, _testmode=True)) == 2

    # no remote defined
    assert len(project.repo.remotes) == 0

    # check we start with no remote -> no failure
    assert not checks.check_has_single_remote(project.repo)

    # we force a new remote -> still no failure
    project.create_branch("origin/remote-name", remote="invalid-url")
    assert not checks.check_has_single_remote(project.repo)

    # if we ask for a non-exhistant remote we fail
    assert checks.check_has_single_remote(project.repo, "origin/remote-name2")

    # adding a second remote
    project.create_branch("origin/remote-name2", remote="another-url")
    assert checks.check_has_single_remote(project.repo)

    # we can explicitly use a remote to refer to (this won't trigger an error)
    assert not checks.check_has_single_remote(project.repo, "origin/remote-name2")


def test_check_initifile(git_project_factory):
    "checks initfile presence and contents"

    # we create a project without an initfile
    project = git_project_factory("check-initfile").create(None)

    # this will dump all issues at once
    assert len(checks.check_initfile(project.initfile, _testmode=True)) == 2

    # initfile not present -> fail
    assert checks.check_initfile(project.initfile)
    assert checks.check_initfile(project.initfile)[0].msg.startswith("no init file")

    project.initfile.parent.mkdir(parents=True, exist_ok=True)

    # touching the file (but still failing because of the missing __version__ variable)
    project.initfile.write_text("")
    assert checks.check_initfile(project.initfile)[0].msg.startswith(
        "cannot find __version__ in"
    )

    # we succeed on well formed initfile
    project.initfile.write_text("__version__ = '1.2.3'")

    # all good
    assert not checks.check_initfile(project.initfile)


def test_check_for_release(git_project_factory):
    project = git_project_factory("check-release").create("0.3.1")
    curver = tools.get_module_var(project.initfile, "__version__", abort=False)
    assert curver == "0.3.1"

    # this will dump all issues at once
    assert (
        len(checks.check_for_release(project.repo, project.initfile, _testmode=True))
        == 4
    )


def test_check_for_release_check_we_are_in_a_beta_branch(git_project_factory):
    "when release we must be on a beta/N.M.O branch"
    project = git_project_factory("check-release").create("0.3.1")
    # curver = tools.get_module_var(project.initfile, "__version__", abort=False)

    # the release starts from a beta branch -> this will fail
    assert (
        checks.check_for_release(project.repo, project.initfile)[0].msg
        == "release should start from 'beta/0.3.1' branch (currently on master)"
    )

    # so we switch on beta/0.3.1
    project.checkout(branch="beta/0.3.1")
    assert project.branch.shorthand == "beta/0.3.1"

    # all good
    assert not checks.check_for_release(project.repo, project.initfile)


def test_check_for_release_check_we_arent_re_releasing(git_project_factory):
    "checking we aren't re-releasing"
    project = git_project_factory("check-release").create("0.3.1")
    # curver = tools.get_module_var(project.initfile, "__version__", abort=False)

    # moving to a beta/0.3.1 branch
    project.checkout(branch="beta/0.3.1")

    # we create a fictional release/0.3.1 tag, this to check we won't re-release
    project.tag("release/0.3.1")

    assert checks.check_for_release(project.repo, project.initfile)[0].msg.startswith(
        "tag release/0.3.1 present, cannot re-release"
    )
    project.repo.references.delete("refs/tags/release/0.3.1")

    # all good
    assert not checks.check_for_release(project.repo, project.initfile)


def test_check_for_release_check_current_branch_is_in_sync_with_remote(
    git_project_factory,
):
    "verify the local beta/* branches are in sync with their remote counterparts"
    # generate a project
    project = git_project_factory("check-release").create("0.0.0")

    # adds a local + remote branch
    project.repo.branches.local.create(
        "beta/0.0.0", project.repo.get(project.repo.head.target)
    )
    project.repo.references.create(
        "refs/remotes/origin/beta/0.0.0", project.repo.head.target
    )

    # new beta branch (local + remote)
    tools.set_module_var(project.initfile, "__version__", "0.1.0")
    project.commit(project.initfile, "updated to 0.1.0")
    project.repo.branches.local.create(
        "beta/0.1.0", project.repo.get(project.repo.head.target)
    )
    project.repo.references.create(
        "refs/remotes/origin/beta/0.1.0", project.repo.head.target
    )

    # make local modification to the beta branch
    project.checkout(branch="beta/0.1.0", exist_ok=True)
    project.initfile.write_text(project.initfile.read_text() + "# hello\n")
    project.commit(project.initfile, "touch file")

    assert (
        checks.check_for_release(project.repo, project.initfile)[0].msg
        == "local and remote branches beta/0.1.0 are out of sync"
    )

    # sync the local (eg. git pull)
    project.repo.references["refs/remotes/origin/beta/0.1.0"].set_target(
        project.repo.branches.local["beta/0.1.0"].target
    )

    # all good
    assert not checks.check_for_release(project.repo, project.initfile)
