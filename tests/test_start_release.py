import re
from unittest import mock
import pytest
import contextlib
import argparse

from setuptools_github import start_release as sr
from setuptools_github import tools


@pytest.fixture(scope="function")
def cli():
    from argparse import Namespace

    with contextlib.ExitStack() as stack:
        mcks = {}
        mcks["release"] = stack.enter_context(
            mock.patch("setuptools_github.start_release.release")
        )
        mcks["beta"] = stack.enter_context(
            mock.patch("setuptools_github.start_release.beta")
        )

        mcks["exit"] = stack.enter_context(
            mock.patch.object(argparse.ArgumentParser, "exit")
        )
        mcks["error"] = stack.enter_context(
            mock.patch.object(argparse.ArgumentParser, "error")
        )
        mcks["_print_message"] = stack.enter_context(
            mock.patch.object(argparse.ArgumentParser, "_print_message")
        )
        yield Namespace(**mcks)


def test_extract_beta_branches(git_project_factory):
    "test the branch and tag extraction function"
    from pygit2 import Repository

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

    repo = Repository(project.workdir)
    assert (local_branches, remote_branches, tags) == sr.extract_beta_branches(repo)

    assert local_branches == ["beta/0.0.1", "beta/0.0.4"]
    assert remote_branches == {
        "origin": ["beta/0.0.3", "beta/0.0.4"],
        "repo1": ["beta/0.0.2"],
    }
    assert tags == ["release/0.0.3", "release/0.0.4"]


@pytest.mark.skipif(True, reason="not-working-in-github")
def test_start_release_repo_has_modifications(cli, git_project_factory):
    "verifies there are no local modified files"
    project = git_project_factory().create()

    # no init file at all -> fail
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "no init file found"
    assert (cli.release.called, cli.beta.called) == (False, False)

    # add initfile, but not commit -> fail
    project.initfile.parent.mkdir(parents=True, exist_ok=True)
    project.initfile.write_text("__version__ = '0.0.0'")
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "init file is not tracked"
    assert (cli.release.called, cli.beta.called) == (False, False)

    # modify committed initfile -> fail
    project(["add", project.initfile])
    project(["commit", "-m", "test", project.initfile])
    project.initfile.write_text("__version__ = '0.0.0'\n")
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "init file has local modifications"
    assert (cli.release.called, cli.beta.called) == (False, False)


def test_start_release_invalid_init(cli, git_project_factory):
    "check the initfile contains at lease the __version__ information"
    project = git_project_factory().create()
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )

    # no init file at all
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "no init file found"
    assert (cli.release.called, cli.beta.called) == (False, False)

    # adds an invalid init file
    project.initfile.parent.mkdir(parents=True, exist_ok=True)
    project.initfile.write_text("hello")
    project(["add", project.initfile])
    project(["commit", "-m", "test", project.initfile])

    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "init file has an invalid __version__ module variable"
    assert (cli.release.called, cli.beta.called) == (False, False)


def test_start_release_invalid_branch(cli, git_project_factory):
    "verify the starting branch for beta and releases"
    project = git_project_factory().create("0.0.0")
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )

    project.branch("abc")
    project(["checkout", "abc"])
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "'micro' starts from 'master' branch"

    options = sr.parse_args(
        ["-w", str(project.workdir), "release", str(project.initfile)], testmode=True
    )
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "release starts from a beta/N.M.O branch"


def test_start_release_invalid_version(cli, git_project_factory):
    "check for beta/release colliding versions"
    repo = git_project_factory("test_start_release_invalid_version-repo").create(
        "0.0.0"
    )
    repo1 = git_project_factory("test_start_release_invalid_version-repo1").create(
        clone=repo
    )

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

    assert project.branch(), project.version == ("master", "0.0.0")

    # cannot re-create a "local" branch
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert (
        exc.message
        == "next version branch 'beta/0.0.1' already present in local branches"
    )

    # cannot re-create a "remote" branch
    project.initfile.write_text("__version__ = '0.0.1'")
    project.commit(project.initfile, "update")
    assert project.branch(), project.version == ("master", "0.0.1")
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert (
        exc.message
        == "next version branch 'beta/0.0.2' already present in remote branches"
    )

    project(["checkout", "beta/0.0.4"])
    assert project.branch(), project.version == ("beta/0.0.4", "0.0.0")

    options = sr.parse_args(
        ["-w", str(project.workdir), "release", str(project.initfile)], testmode=True
    )
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "wrong version '0.0.0' from initfile"


def test_start_cli_help(cli):
    "test the --help flag to the cli"
    sr.parse_args(["--help"], testmode=True)

    # we show only the help
    assert (cli.release.called, cli.beta.called) == (False, False)

    def s(txt):
        result = re.sub(r"\s(\s*)", " ", txt.strip())
        if ".py optional arguments:" in result:
            result = result.replace(".py optional arguments:", ".py options:")
        return result

    assert s(cli._print_message.call_args.args[0]) == s(
        """
usage: AAAA [-h] [-n] [-v] [--master MASTER] [-w WORKDIR]
                            {micro,minor,major,release} __init__.py

positional arguments:
  {micro,minor,major,release}
  __init__.py

options:
  -h, --help            show this help message and exit
  -n, --dry-run
  -v, --verbose
  --master MASTER       the 'master' branch (default: master)
  -w WORKDIR, --workdir WORKDIR
                        git working dir (default: .)
"""
    )


@pytest.mark.skipif(True, reason="not-working-in-github")
def test_start_release_safe_beta_cli(cli, git_project_factory):
    "test the cli usage for beta releases up to the beta execution"
    project = git_project_factory("test_start_release_beta_repo").create()

    # we start with an empty repo
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "no init file found"

    # we add an (invalid) init file
    project.initfile.parent.mkdir(parents=True, exist_ok=True)
    project.initfile.write_text("hello")
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "init file is not tracked"

    # we track it (but no commit)
    project(["add", project.initfile])
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "init file has local modifications"

    # we commit changes (still has no __version__ in it)
    project(["commit", "-m", "initial"])
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "init file has an invalid __version__ module variable"

    # ok we fix the __version__
    project.initfile.write_text("__version__ = '0.0.0'")
    project(["commit", "-m", "start", project.initfile])

    # and we verify we're able to call the beta function
    assert (cli.release.called, cli.beta.called) == (False, False)
    sr.run(**options)
    assert (cli.release.called, cli.beta.called) == (False, True)


def test_start_release_safe_release_cli(cli, git_project_factory):
    "test the cli usage for a release up to the release execution"

    project = git_project_factory().create("0.0.0")
    assert (project.branch(), project.version) == ("master", "0.0.0")

    # we start on master (eg. we cannot start a release)
    options = sr.parse_args(
        ["-w", str(project.workdir), "release", str(project.initfile)], testmode=True
    )
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "release starts from a beta/N.M.O branch"

    # ok we can start a beta release here
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )
    sr.run(**options)
    assert (cli.release.called, cli.beta.called) == (False, True)
    cli.beta.reset_mock()

    # we start a release from a named branch
    project.branch("beta/0.0.0")
    assert (project.branch(), project.version) == ("beta/0.0.0", "0.0.0")
    options = sr.parse_args(
        ["-w", str(project.workdir), "release", str(project.initfile)], testmode=True
    )
    sr.run(**options)
    assert (cli.release.called, cli.beta.called) == (True, False)


def test_start_release_e2e(git_project_factory):
    "full end2end walkthrough scenario"
    project = git_project_factory().create("0.0.1")
    assert (project.branch(), project.version) == ("master", "0.0.1")

    # creating a first branch (note as we won't bump 0.0.1 because is
    # the first beta branch)
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )
    sr.run(**options)
    assert (project.branch(), project.version) == ("beta/0.0.1", "0.0.1")

    # try a beta release from a beta branch should fail
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "'micro' starts from 'master' branch"

    # trying a second branch
    project(["checkout", "master"])
    assert (project.branch(), project.version) == ("master", "0.0.1")

    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )
    sr.run(**options)
    assert (project.branch(), project.version) == ("beta/0.0.2", "0.0.2")

    # again we won't be able to start a new branch from a non master branch
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "'micro' starts from 'master' branch"

    # two more betas
    project(["checkout", "master"])
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )
    sr.run(**options)
    assert (project.branch(), project.version) == ("beta/0.0.3", "0.0.3")

    project(["checkout", "master"])
    options = sr.parse_args(
        ["-w", str(project.workdir), "micro", str(project.initfile)], testmode=True
    )
    sr.run(**options)
    assert (project.branch(), project.version) == ("beta/0.0.4", "0.0.4")

    # let's finally release 0.0.3 here (first we verify we cannot release
    # from a non master branch)
    project(["checkout", "beta/0.0.3"])
    exc = pytest.raises(tools.AbortExecution, sr.run, **options).value
    assert exc.message == "'micro' starts from 'master' branch"

    assert not project(["tag", "-l"]).split()
    options = sr.parse_args(
        ["-w", str(project.workdir), "release", str(project.initfile)], testmode=True
    )
    sr.run(**options)
    assert project(["tag", "-l"]).split() == ["release/0.0.3"]
