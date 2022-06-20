import pytest

from setuptools_github import start_release as sr


def test_create_beta_no_init_failure(git_project_factory):
    "start a beta branch with a missing init"
    project = git_project_factory("no-init-file").create(None)

    args = [
        "--workdir",
        project.workdir,
        "minor",
        project.initfile,
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    checks = sr.run(_dont_exit=True, **kwargs)
    assert len(checks) == 1
    assert checks[0].msg.startswith("no init file ")


def test_create_beta_not_in_mater(git_project_factory):
    "start a beta branch within a no-master branch"
    project = git_project_factory("not-in-master").create("0.0.0")
    project.checkout(branch="non-master")

    args = [
        "--workdir",
        project.workdir,
        "minor",
        project.initfile,
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    checks = sr.run(_dont_exit=True, **kwargs)
    assert len(checks) == 1
    assert checks[0].msg.startswith("current branch is ")


def test_create_beta_has_modifications(git_project_factory):
    "start a beta branch with local modifications"
    project = git_project_factory("local-mods").create("0.0.0")

    # adds a new file, commit and modify
    path = project.initfile.parent / "abc.txt"
    path.write_text("abc")
    project.commit(path, "test file")
    path.write_text("def")

    args = [
        "--workdir",
        project.workdir,
        "minor",
        project.initfile,
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    checks = sr.run(_dont_exit=True, **kwargs)
    assert len(checks) == 1
    assert checks[0].msg.startswith("local modifications present ")


def test_create_beta_multiple_remotes(git_project_factory):
    "start a beta branch with multiple remotes"
    project = git_project_factory("multiple-remotes").create("0.0.0")

    # adds a new remote
    project.create_remote("another-remote")

    args = [
        "--workdir",
        project.workdir,
        "minor",
        project.initfile,
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    checks = sr.run(_dont_exit=True, **kwargs)
    assert len(checks) == 1
    assert checks[0].msg.startswith("multiple remotes defined: ")


# .create("0.0.3")

#     assert project.branch == "master"
#     assert project.version == "0.0.3"
#
#     # create the first beta branch:
#     #  we checkout the beta/0.0.3 branch
#     #  the version stays the same as master
#     args = [
#         "--workdir",
#         project.workdir,
#         "minor",
#         project.initfile,
#     ]
#     kwargs = sr.parse_args([str(a) for a in args])
#     sr.run(**kwargs)
#     assert project.branch == "beta/0.0.3"
#     assert project.version == "0.0.3"
#     return
#
#     # make sure we cannot re-apply in a non-master branch
#     pytest.raises(SystemExit, sr.run, **kwargs)
#     project.checkout("master")
#
#     # second round to create a beta branch
#     #  we update the __init__.py to 0.1.0 (minor) in master
#     assert project.branch == "master"
#     assert project.version == "0.0.3"
#
#     sr.run(**kwargs)
#     assert project.branch == "beta/0.1.0"
#     assert project.version == "0.1.0"
#
#     # verify master branch has the version matching the beta
#     project.checkout("master")
#     assert project.branch == "master"
#     assert project.version == "0.1.0"
#
#
# def test_end2end_release(git_project_factory):
#     "end2end run for a release"
#     project = git_project_factory("projectXX").create("0.1.0")
#     assert project.branch == "master"
#     assert project.version == "0.1.0"
#
#     # we try to release from master, without first going through a beta first
#     # -> we fail
#     args = [
#         "--workdir",
#         project.workdir,
#         "release",
#         project.initfile,
#     ]
#     kwargs = sr.parse_args([str(a) for a in args])
#     kwargs["_dont_exit"] = True
#     pytest.raises(RuntimeError, sr.run, **kwargs)
#
#     # so we first create a new beta branch (beta/0.1.0 because there isn't a beta branch)
#     args = [
#         "--workdir",
#         project.workdir,
#         "minor",
#         project.initfile,
#     ]
#     kwargs = sr.parse_args([str(a) for a in args])
#     kwargs["_dont_exit"] = True
#     sr.run(**kwargs)
#     assert project.branch == "beta/0.1.0"
#     #assert project.version == "0.1.0"
#
#     # HERE
#     return
#
#     # try to release on the non master branch (and fail again)
#     args = [
#         "--workdir",
#         project.workdir,
#         "release",
#         project.initfile,
#     ]
#     kwargs = sr.parse_args([str(a) for a in args])
#     pytest.raises(SystemExit, sr.run, **kwargs)
#     assert project.branch == "beta/0.1.0"
#     assert project.version == "0.1.0"
#
#     project.checkout("master")
#     args = [
#         "--workdir",
#         project.workdir,
#         "release",
#         project.initfile,
#     ]
#     kwargs = sr.parse_args([str(a) for a in args])
#     sr.run(**kwargs)
#     assert project.branch == "beta/0.1.0"
#     assert project.version == "0.1.0"
