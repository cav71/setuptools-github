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


def T(txt):
    from textwrap import dedent

    txt = dedent(txt)
    if txt.startswith("\n"):
        txt = txt[1:]
    return txt


def T1(txt):
    return T(txt).rstrip("\n")


def test_abort_exception():
    "test the AbortExecution exception"
    a = tools.AbortExecution(
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
        f"\n{str(a)}\n"
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

    a = tools.AbortExecution("hello world")
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
    pytest.raises(AssertionError, tools.get_module_var, path, "B")
    pytest.raises(tools.MissingVariable, tools.get_module_var, path, "X1")


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


def test_update_version(tmp_path):
    "test the update_version processing"
    from hashlib import sha224

    def writeinit(path, version="1.2.3"):
        path.write_text(
            f"""
# a test file
__version__ = "{version}"
__hash__ = "4.5.6"

# end of test
"""
        )
        return sha224(path.read_bytes()).hexdigest()

    initfile = tmp_path / "__init__.py"
    hashval = writeinit(initfile)

    # verify nothing has changed
    assert "1.2.3" == tools.update_version(initfile, abort=False)
    assert hashval == sha224(initfile.read_bytes()).hexdigest()

    # we update the __version__/__hash__ from a master branch
    tools.update_version(initfile, GITHUB["master"])
    assert (
        initfile.read_text()
        == """
# a test file
__version__ = "1.2.3"
__hash__ = "2169f90c"

# end of test
"""
    )

    # we update __version__/__hash__ from a beta branch (note the b<build-number>)
    writeinit(initfile)
    pytest.raises(tools.GithubError, tools.update_version, initfile, GITHUB["beta"])

    writeinit(initfile, "0.0.4")
    tools.update_version(initfile, GITHUB["beta"])
    assert (
        initfile.read_text()
        == """
# a test file
__version__ = "0.0.4b8"
__hash__ = "2169f90c22e"

# end of test
"""
    )

    writeinit(initfile)
    pytest.raises(tools.GithubError, tools.update_version, initfile, GITHUB["release"])

    writeinit(initfile, "0.0.3")
    tools.update_version(initfile, GITHUB["release"])
    assert (
        initfile.read_text()
        == """
# a test file
__version__ = "0.0.3"
__hash__ = "5547365c82"

# end of test
"""
    )


def test_e2e(git_project_factory):
    repo = git_project_factory().create()

    pytest.raises(tools.MissingVariable, tools.update_version, repo.initfile, None)

    # adds a new version file on the master branch
    assert repo.branch() == "master"
    assert repo.version("0.0.4") == "0.0.4"
    assert repo.initfile.read_text() == T(
        """
    __version__ = "0.0.4"
    """
    )

    # update the local version (manual build)
    assert tools.update_version(repo.initfile, None) == "0.0.4"
    assert tools.update_version(repo.initfile, GITHUB["master"]) == "0.0.4"
    assert repo.initfile.read_text() == T1(
        """
    __version__ = "0.0.4"
    __hash__ = "2169f90c"
    """
    )

    # branch for beta
    repo.branch("beta/0.0.4", "master")
    assert repo.branch() == "beta/0.0.4"

    tools.update_version(repo.initfile, None)
    repo.revert()
    assert repo.version() == "0.0.4"

    assert tools.update_version(repo.initfile, GITHUB["beta"]) == "0.0.4b8"
    repo(["commit", "-m", "change", repo.initfile])
    assert repo.version() == "0.0.4b8"

    # branch/tag for release
    repo.branch("release/0.0.3", "master")
    assert repo.branch() == "release/0.0.3"
    repo.version("0.0.3")

    tools.update_version(repo.initfile, None)
    assert repo.version() == "0.0.3"
    assert tools.update_version(repo.initfile, GITHUB["release"]) == "0.0.3"
