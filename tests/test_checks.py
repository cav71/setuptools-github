# import pytest
#
# from setuptools_github import checks, tools
#
#
# def error(message: str, explain: str = "", hint: str = ""):
#     raise tools.AbortExecution(message, explain, hint)
#
#
# def test_check_initfile(git_project_factory):
#     project = git_project_factory().create()
#
#     exc = pytest.raises(
#         tools.AbortExecution, checks.check_initfile, error, project.initfile
#     ).value
#     assert """
# no init file found
#   An init file (eg. __init__.py) should be defined containing
#   a __version__ = "<major>.<minor>.<micro>" version
# hint:
#   add an init file in""".strip() in str(
#         exc
#     )
#
#     # add an empty init file
#     project.initfile.parent.mkdir(parents=True)
#     project.initfile.write_text("hello =  1\n")
#
#     exc = pytest.raises(
#         tools.AbortExecution, checks.check_initfile, error, project.initfile
#     ).value
#     assert """
# init file has an invalid __version__ module variable
#   An init file (eg. __init__.py) should be defined containing
#   a __version__ = "<major>.<minor>.<micro>" version
# hint:
#   add a __version__ module variable in""".strip() in str(
#         exc
#     )
#
#
# def test_check_branch(git_project_factory):
#     project = git_project_factory().create("0.0.3")
#     assert project.branch() == "master"
#
#     pytest.raises(
#         RuntimeError, checks.check_branch, error, "no-value", project.branch()
#     )
#
#     # switch branch
#     old = project.branch("abc")
#     assert (old, project.branch()) == ("master", "abc")
#
#     # check we cannot start from that branch
#     exc = pytest.raises(
#         tools.AbortExecution, checks.check_branch, error, "minor", project.branch()
#     ).value
#     assert """
# 'minor' starts from 'master' branch
#   While generating a branch for 'minor' we assume as starting
#   branch to be 'master' but we are in 'abc'.
# hint:
#   Switch to the 'master' branch or pass the --master flag
# """.strip() in str(
#         exc
#     )
#
#     # we force the master to be 'abc'
#     assert not checks.check_branch(error, "minor", project.branch(), master="abc")
#
#     # starting a release branch
#     exc = pytest.raises(
#         tools.AbortExecution,
#         checks.check_branch,
#         error,
#         "release",
#         project.branch(),
#         master="abc",
#     ).value
#     assert """
# release starts from a beta/N.M.O branch
#   A release starts from a beta/N.M.O branch, not from 'abc'
# hint:
#   switch to a beta/N.M.O branch
# """.strip() in str(
#         exc
#     )
#
#     project.branch("beta/1.2.3")
#     assert not checks.check_branch(error, "release", project.branch(), master="abc")
#
#
# def test_check_version(git_project_factory):
#     from setuptools_github.scm import extract_beta_branches_and_release_tags
#
#     repo = git_project_factory("test_check_version-repo").create("0.0.0")
#     repo1 = git_project_factory("test_check_version-repo1").create(clone=repo)
#
#     repo.branch("beta/0.0.3")
#     repo(["tag", "-m", "release", "release/0.0.3"])
#     repo.branch("beta/0.0.4")
#     repo(["tag", "-m", "release", "release/0.0.4"])
#     repo1.branch("beta/0.0.2")
#
#     project = git_project_factory().create(clone=repo)
#     project.branch("beta/0.0.1", "origin/master")
#     project.branch("master", "origin/master")
#
#     project(["remote", "add", "repo1", repo1.workdir])
#     project(["fetch", "--all"])
#
#     local_branches, remote_branches, tags = [
#         *project.branches(project.BETA_BRANCHES),
#         project(["tag", "-l"]).split(),
#     ]
#     from pygit2 import Repository
#
#     repo = Repository(project.workdir)
#     assert (
#         local_branches,
#         remote_branches,
#         tags,
#     ) == extract_beta_branches_and_release_tags(repo)
#
#     assert project.branch() == "master"
#     assert project.version() == "0.0.0"
#
#     exc = pytest.raises(
#         tools.AbortExecution,
#         checks.check_version,
#         error,
#         "micro",
#         project.initfile,
#         project.branch(),
#         local_branches,
#         remote_branches,
#         tags,
#         "master",
#     ).value
#     assert """
# next version branch 'beta/0.0.1' already present in local branches
#   when creating a new branch 'beta/0.0.1' a local branch
#   with that name has been found already
# hint:
#   change the version from '0.0.0' in the 'master' branch initfile
# """.strip() in str(
#         exc
#     )
#
#     project.initfile.write_text("__version__ = '0.0.1'")
#     project.commit(project.initfile, "update")
#     exc = pytest.raises(
#         tools.AbortExecution,
#         checks.check_version,
#         error,
#         "micro",
#         project.initfile,
#         project.branch(),
#         local_branches,
#         remote_branches,
#         tags,
#         "master",
#     ).value
#     assert """
# next version branch 'beta/0.0.2' already present in remote branches
#   when creating a new branch 'beta/0.0.2' a remote branch with
#   that name has been found already in 'repo1'
# hint:
#   make sure the '0.0.1' in the initfile in 'master' branch is correct
# """.strip() in str(
#         exc
#     )
#
#     project.initfile.write_text("__version__ = '0.0.4'")
#     project.commit(project.initfile, "update")
#     assert not checks.check_version(
#         error,
#         "micro",
#         project.initfile,
#         project.branch(),
#         local_branches,
#         remote_branches,
#         tags,
#         "master",
#     )
#
#     # release checks
#     project(["checkout", "beta/0.0.4"])
#     project(["merge", "master"])
#     assert (project.branch(), project.version()) == ("beta/0.0.4", "0.0.4")
#
#     exc = pytest.raises(
#         tools.AbortExecution,
#         checks.check_version,
#         error,
#         "release",
#         project.initfile,
#         project.branch(),
#         local_branches,
#         remote_branches,
#         tags,
#         "master",
#     ).value
#     assert """
# release already prsent
#   A release 'release/0.0.4' tag is present for the current branch
# hint:
#   check the __version__ is correct
# """.strip() in str(
#         exc
#     )
