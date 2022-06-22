from setuptools_github import checks, tools


class ErrorHandler:
    def __init__(self):
        self.issue = None

    def __call__(self, message, explain="", hint=""):
        self.issue = tools.AbortExecution(message, explain, hint)


def test_check_initfile(git_project_factory):
    project = git_project_factory().create()

    error = ErrorHandler()
    checks.check_initfile(error, project.initfile)
    assert """
no init file found
  An init file (eg. __init__.py) should be defined containing
  a __version__ = "<major>.<minor>.<micro>" version
hint:
  add an init file in""".strip() in str(
        error.issue
    )

    # add an empty init file
    project.initfile.parent.mkdir(parents=True)
    project.initfile.write_text("hello =  1\n")

    checks.check_initfile(error, project.initfile)
    assert """
init file has an invalid __version__ module variable
  An init file (eg. __init__.py) should be defined containing
  a __version__ = "<major>.<minor>.<micro>" version
hint:
  add a __version__ module variable in""".strip() in str(
        error.issue
    )


def test_check_branch(git_project_factory):
    project = git_project_factory().create("0.0.3")

    assert project.branch() == "master"

    # switch branch
    old = project.branch("abc")
    assert (old, project.branch()) == ("master", "abc")

    # check we cannot start from that branch
    error = ErrorHandler()
    checks.check_branch(error, "minor", project.branch())
    assert """
'minor' starts from 'master' branch
  While generating a branch for 'minor' we assume as starting
  branch to be 'master' but we are in 'abc'.
hint:
  Switch to the 'master' branch or pass the --master flag
""".strip() in str(
        error.issue
    )

    # we force the master to be 'abc'
    error = ErrorHandler()
    checks.check_branch(error, "minor", project.branch(), master="abc")
    assert not error.issue

    # starting a release branch
    error = ErrorHandler()
    checks.check_branch(error, "release", project.branch(), master="abc")
    assert """
release starts from a beta/N.M.O branch
  A release starts from a beta/N.M.O branch, not from 'abc'
hint:
  switch to a beta/N.M.O branch
""".strip() in str(
        error.issue
    )

    project.branch("beta/1.2.3")
    error = ErrorHandler()
    checks.check_branch(error, "release", project.branch(), master="abc")
    assert not error.issue


def test_check_version(git_project_factory):
    from setuptools_github.start_release import extract_beta_branches

    repo = git_project_factory("test_check_version-repo").create("0.0.0")
    repo1 = git_project_factory("test_check_version-repo1").create(clone=repo)

    repo.branch("beta/0.0.3")
    repo(["tag", "-m", "release", "release/0.0.3"])
    repo.branch("beta/0.0.4")
    repo(["tag", "-m", "release", "release/0.0.4"])
    repo1.branch("beta/0.0.2")

    project = git_project_factory().create(clone=repo)
    project.branch("beta/0.0.1", "origin/master")
    project.branch("master", "origin/master")

    project(["remote", "add", "repo1", repo1.workdir])
    project(["fetch", "--all"])

    local_branches, remote_branches, tags = [
        *project.branches(),
        project(["tag", "-l"]).split(),
    ]
    from pygit2 import Repository

    repo = Repository(project.workdir)
    assert (local_branches, remote_branches, tags) == extract_beta_branches(repo)

    assert project.branch() == "master"
    assert project.version == "0.0.0"

    error = ErrorHandler()
    checks.check_version(
        error,
        "micro",
        project.initfile,
        local_branches,
        remote_branches,
        tags,
        project.branch(),
    )
    assert """
next version branch 'beta/0.0.1' already present in local branches
  when creating a new branch 'beta/0.0.1' a local branch
  with that name has been found already
hint:
  change the version from '0.0.0' in the 'master' branch initfile
""".strip() in str(
        error.issue
    )

    project.initfile.write_text("__version__ = '0.0.1'")
    project.commit(project.initfile, "update")
    error = ErrorHandler()
    checks.check_version(
        error,
        "micro",
        project.initfile,
        local_branches,
        remote_branches,
        tags,
        project.branch(),
    )
    assert """
next version branch 'beta/0.0.2' already present in remote branches
  when creating a new branch 'beta/0.0.2' a remote branch with
  that name has been found already in 'repo1'
hint:
  make sure the '0.0.1' in the initfile in 'master' branch is correct
""".strip() in str(
        error.issue
    )

    project.initfile.write_text("__version__ = '0.0.4'")
    project.commit(project.initfile, "update")
    error = ErrorHandler()
    checks.check_version(
        error,
        "micro",
        project.initfile,
        local_branches,
        remote_branches,
        tags,
        project.branch(),
    )
    assert not error.issue

    # release checks
    project(["checkout", "beta/0.0.4"])
    project(["merge", "master"])
    assert (project.branch(), project.version) == ("beta/0.0.4", "0.0.4")

    error = ErrorHandler()
    checks.check_version(
        error,
        "release",
        project.initfile,
        local_branches,
        remote_branches,
        tags,
        project.branch(),
    )
    assert """
release already prsent
  A release 'release/0.0.4' tag is present for the current branch
hint:
  check the __version__ is correct
""".strip() in str(
        error.issue
    )
