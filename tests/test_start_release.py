import contextlib
import pygit2  # type: ignore
import pytest

from setuptools_github import start_release as sr


class Project:
    def __init__(self, dst, repo=None):
        self.dst = dst
        self.repo = repo

    def create(self, version, dst=None):
        dst = dst or self.dst

        pygit2.init_repository(dst)
        self.repo = repo = pygit2.Repository(dst)

        repo.config["user.name"] = "myusername"
        repo.config["user.email"] = "myemail"

        (dst / "src").mkdir(parents=True, exist_ok=True)
        (dst / "src" / "__init__.py").write_text(
            f"""
__version__ = "{version}"
""".lstrip()
        )

        repo.index.add("src/__init__.py")
        tree = repo.index.write_tree()

        sig = pygit2.Signature("no-body", "a.b.c@example.com")
        repo.create_commit("HEAD", sig, sig, "hello", tree, [])
        return self

    @property
    def version(self):
        return (
            (self.dst / "src/__init__.py")
            .read_text()
            .partition("=")[2]
            .strip()
            .strip('"')
        )

    @property
    def branch(self):
        return self.repo.head.shorthand

    def checkout(self, name):
        cur = self.branch
        ref = self.repo.lookup_reference(self.repo.lookup_branch(name).name)
        self.repo.checkout(ref)
        return cur

    @contextlib.contextmanager
    def in_branch(self, name):
        original = self.checkout(name)
        yield original
        self.checkout(original)


def test_bump_version():
    assert "0.0.2" == sr.bump_version("0.0.1", "micro")
    assert "0.0.3" == sr.bump_version("0.0.2", "micro")

    assert "0.1.0" == sr.bump_version("0.0.2", "minor")

    assert "2.0.0" == sr.bump_version("1.2.3", "major")


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


def test_end2end_betas(tmp_path, capsys):
    "end2end run for a beta branch"

    project = Project(tmp_path / "project").create("0.0.3")
    assert project.branch == "master"
    assert project.version == "0.0.3"

    # create the first beta branch:
    #  we checkout the beta/0.0.3 branch
    #  the version stays the same as master
    args = [
        "-w",
        tmp_path / "project",
        "minor",
        tmp_path / "project/src/__init__.py",
        "--no-checks",
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    sr.run(**kwargs)
    assert project.branch == "beta/0.0.3"
    assert project.version == "0.0.3"

    # make sure we cannot re-apply in a non-master branch
    pytest.raises(SystemExit, sr.run, **kwargs)

    # second round to create a beta branch
    #  we update the __init__.py to 0.1.0 (minor) in master
    #  we checkout the beta/0.0.4 branch
    project.checkout("master")
    assert project.branch == "master"
    assert project.version == "0.0.3"

    sr.run(**kwargs)
    assert project.branch == "beta/0.1.0"
    assert project.version == "0.1.0"

    project.checkout("master")
    assert project.branch == "master"
    assert project.version == "0.1.0"


def test_end2end_release(git_project_factory, capsys):
    "end2end run for a release"
    project = git_project_factory("project1").create("0.1.0")
    assert project.branch == "master"
    assert project.version == "0.1.0"

    args = [
        "-w",
        project.dst,
        "release",
        project.initfile,
        "--no-checks",
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    sr.run(**kwargs)
    return
