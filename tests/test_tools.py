import pytest

from setuptools_github import tools

# this is the output from ${{ toJson(github) }}
GITHUB = {
    "beta": {
        "ref": "refs/heads/beta/0.0.4",
        "sha": "2169f90c22e",
        "run_number": "8",
    },
    "release": {
        "ref": "refs/tags/release/0.0.3",
        "sha": "5547365c82",
        "run_number": "3",
    },
    "master": {
        "ref": "refs/heads/master",
        "sha": "2169f90c",
        "run_number": "20",
    },
}


def T(txt):  # noqa: N802
    from textwrap import dedent

    txt = dedent(txt)
    if txt.startswith("\n"):
        txt = txt[1:]
    return txt


def T1(txt):  # noqa: N802
    return T(txt).rstrip("\n")


def test_abort_exception():
    "test the AbortExecution exception"
    a = tools.AbortExecutionError(
        "a one-line error message",
        """
        A multi line
          explaination of
           what happened
         with some detail
    """,
        """
    Another multiline hint how
      to fix the issue
    """,
    )

    assert a.message == "a one-line error message"
    assert (
        f"\n{a.explain}\n"
        == """
A multi line
  explaination of
   what happened
 with some detail
"""
    )
    assert (
        f"\n{a.hint}\n"
        == """
Another multiline hint how
  to fix the issue
"""
    )

    assert (
        f"\n{a!s}\n"
        == """
a one-line error message
  A multi line
    explaination of
     what happened
   with some detail
hint:
  Another multiline hint how
    to fix the issue
"""
    )

    a = tools.AbortExecutionError("hello world")
    assert a.message == "hello world"
    assert a.explain == ""
    assert a.hint == ""
    assert str(a) == "hello world"


def test_urmtree(tmp_path):
    target = tmp_path / "abc" / "def"
    target.mkdir(parents=True, exist_ok=True)
    assert target.exists()

    tools.urmtree(target)
    assert not target.exists()
    assert target.parent.exists()


def test_indent():
    txt = """
    This is a simply
       indented text
      with some special
         formatting
"""
    expected = """
..This is a simply
..   indented text
..  with some special
..     formatting
"""

    found = tools.indent(txt[1:], "..")
    assert f"\n{found}" == expected


def test_list_of_paths():
    from pathlib import Path

    assert tools.list_of_paths([]) == []
    assert tools.list_of_paths("hello") == [Path("hello")]
    assert tools.list_of_paths(["hello", Path("world")]) == [
        Path("hello"),
        Path("world"),
    ]


def test_get_module_var(tmp_path):
    "pulls variables from a file"
    path = tmp_path / "in0.txt"
    path.write_text(
        """
# a test file
A = 12
B = 3+5
C = "hello"
# end of test
"""
    )
    assert 12 == tools.get_module_var(path, "A")
    assert "hello" == tools.get_module_var(path, "C")
    pytest.raises(tools.ValidationError, tools.get_module_var, path, "B")
    pytest.raises(tools.MissingVariableError, tools.get_module_var, path, "X1")


def test_set_module_var(tmp_path):
    "handles set_module_var cases"
    path = tmp_path / "in2.txt"

    path.write_text(
        """
# a fist comment line
__hash__ = "4.5.6"
# end of test
"""
    )

    version, txt = tools.set_module_var(path, "__version__", "1.2.3")
    assert not version
    assert (
        txt.rstrip()
        == """
# a fist comment line
__hash__ = "4.5.6"
# end of test
__version__ = "1.2.3"
""".rstrip()
    )

    version, txt = tools.set_module_var(path, "__version__", "6.7.8")
    assert version == "1.2.3"
    assert (
        txt.rstrip()
        == """
# a fist comment line
__hash__ = "4.5.6"
# end of test
__version__ = "6.7.8"
""".rstrip()
    )

    version, txt = tools.set_module_var(path, "__hash__", "9.10.11")
    assert version == "4.5.6"
    assert (
        txt.rstrip()
        == """
# a fist comment line
__hash__ = "9.10.11"
# end of test
__version__ = "6.7.8"
""".rstrip()
    )


def test_set_module_var_empty_file(tmp_path):
    "check if the set_module_var will create a bew file"
    path = tmp_path / "in1.txt"

    assert not path.exists()
    tools.set_module_var(path, "__version__", "1.2.3")

    assert path.exists()
    path.write_text("# a fist comment line\n" + path.read_text().strip())

    tools.set_module_var(path, "__hash__", "4.5.6")
    assert (
        path.read_text().strip()
        == """
# a fist comment line
__version__ = "1.2.3"
__hash__ = "4.5.6"
""".strip()
    )


def test_bump_version():
    "bump version test"
    assert tools.bump_version("0.0.1", "micro") == "0.0.2"
    assert tools.bump_version("0.0.2", "micro") == "0.0.3"
    assert tools.bump_version("0.0.2", "minor") == "0.1.0"
    assert tools.bump_version("1.2.3", "major") == "2.0.0"
    assert tools.bump_version("1.2.3", "release") == "1.2.3"


def test_update_version_master(git_project_factory):
    "test the update_version processing on the master branch"

    repo = git_project_factory().create("1.2.3")
    assert tools.get_module_var(repo.initfile) == "1.2.3"

    # verify nothing has changed
    assert "1.2.3" == tools.update_version(repo.initfile, abort=False)
    assert tools.get_module_var(repo.initfile) == "1.2.3"
    assert (
        tools.get_module_var(repo.initfile, "__hash__")
        == repo(["rev-parse", "HEAD"])[:7]
    )

    assert "1.2.3" == tools.update_version(repo.initfile, GITHUB["master"], abort=False)
    assert tools.get_module_var(repo.initfile) == "1.2.3"
    assert tools.get_module_var(repo.initfile, "__hash__") == "2169f90c"


def test_update_version_beta(git_project_factory):
    "test the update_version processing on the master branch"

    repo = git_project_factory().create("0.0.4")
    assert tools.get_module_var(repo.initfile) == "0.0.4"
    assert repo.branch() == "master"

    # branch
    repo.branch("beta/0.0.4", "master")
    assert repo.branch() == "beta/0.0.4"

    assert tools.update_version(repo.initfile, abort=False)
    assert tools.get_module_var(repo.initfile) == "0.0.4b0"
    assert (
        tools.get_module_var(repo.initfile, "__hash__")
        == repo(["rev-parse", "HEAD"])[:7]
    )
    repo.revert(repo.initfile)

    assert tools.get_module_var(repo.initfile) == "0.0.4"
    assert tools.update_version(repo.initfile, GITHUB["beta"], abort=False)
    assert tools.get_module_var(repo.initfile) == "0.0.4b8"
    assert tools.get_module_var(repo.initfile, "__hash__") == "2169f90c22e"
    repo.revert(repo.initfile)

    # wrong branch
    repo.branch("beta/0.0.2", "master")
    assert repo.branch() == "beta/0.0.2"
    pytest.raises(
        tools.InvalidVersionError, tools.update_version, repo.initfile, abort=False
    )

    github_dump = GITHUB["beta"].copy()
    github_dump["ref"] = "refs/heads/beta/0.0.2"
    pytest.raises(
        tools.InvalidVersionError,
        tools.update_version,
        repo.initfile,
        github_dump,
        abort=False,
    )


def test_update_version_release(git_project_factory):
    repo = git_project_factory().create("0.0.3")
    assert tools.get_module_var(repo.initfile) == "0.0.3"

    # branch
    repo.branch("beta/0.0.3", "master")
    assert repo.branch() == "beta/0.0.3"

    path = repo.workdir / "hello.txt"
    path.write_text("hello world\n")
    repo.commit(path, "initial")

    repo(["tag", "release/0.0.3", repo(["rev-parse", "HEAD"])[:7]])

    assert (
        tools.update_version(repo.initfile, GITHUB["release"], abort=False) == "0.0.3"
    )
    assert tools.get_module_var(repo.initfile) == "0.0.3"
    assert tools.get_module_var(repo.initfile, "__hash__") == "5547365c82"
    repo.revert(repo.initfile)
