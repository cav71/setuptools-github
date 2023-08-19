# ruff: noqa: E501
import json

import pytest
from setuptools_github import tools

# this is the output from ${{ toJson(github) }}
GITHUB = {
    "beta": {
        "ref": "refs/heads/beta/0.3.10",
        "sha": "507c657056d1a66520ec6b219a64706e70b0ff15",
        "run_number": "98",
        "run_id": "5904313530",
    },
    "release": {
        "ref": "refs/tags/release/0.3.9",
        "sha": "2b79a3669cd06e21741f6ee7a271903482344e76",
        "run_number": "22",
        "run_id": "5789585760",
    },
    "master": {
        "ref": "refs/heads/master",
        "sha": "9df889992f422a62cdd3ced41323eaba6e855ae3",
        "run_number": "257",
        "run_id": "5789314202",
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


def test_lstrip():
    assert tools.lstrip("/a/b/c/d/e", "/a/b") == "/c/d/e"


def test_apply_fixers():
    fixers = {
        "abc": "def",
    }
    assert tools.apply_fixers("abcdef abc123", fixers) == "defdef def123"
    fixers = {
        "re:([ab])cde": "x\\1",
    }
    assert tools.apply_fixers("acde bcde123", fixers) == "xa xb123"

    fixers = {
        # for the github actions
        "re:(https://github.com/.+/actions/workflows/)(master)(.yml/badge.svg)": "\\1{{ ctx.workflow }}\\3",
        "re:(https://github.com/.+/actions)/(workflows/)(master.yml)(?!/)": "\\1/runs/{{ ctx.runid }}",
        # for the codecov part
        "re:(https://codecov.io/gh/.+/tree)/master(/graph/badge.svg[?]token=.+)": "\\1/{{ ctx.branch|urlquote }}\\2",
        "re:(https://codecov.io/gh/.+/tree)/master(?!/)": "\\1/{{ ctx.branch|urlquote }}",
    }

    txt = "https://github.com/cav71/setuptools-github/actions/workflows/master.yml/badge.svg"
    expected = "https://github.com/cav71/setuptools-github/actions/workflows/{{ ctx.workflow }}.yml/badge.svg"
    assert tools.apply_fixers(txt, fixers) == expected

    txt = "https://github.com/cav71/setuptools-github/actions/workflows/master.yml"
    expected = "https://github.com/cav71/setuptools-github/actions/runs/{{ ctx.runid }}"
    assert tools.apply_fixers(txt, fixers) == expected

    txt = "https://codecov.io/gh/cav71/setuptools-github/tree/master/graph/badge.svg?token=RANDOM123"
    expected = "https://codecov.io/gh/cav71/setuptools-github/tree/{{ ctx.branch|urlquote }}/graph/badge.svg?token=RANDOM123"
    assert tools.apply_fixers(txt, fixers) == expected

    txt = "https://codecov.io/gh/cav71/setuptools-github/tree/master"
    expected = (
        "https://codecov.io/gh/cav71/setuptools-github/tree/{{ ctx.branch|urlquote }}"
    )
    assert tools.apply_fixers(txt, fixers) == expected


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

    path.write_text(
        """
# a test file
A = 12
B = 3+5
C = "hello"
C = "hello2"
# end of test
"""
    )
    pytest.raises(tools.ValidationError, tools.get_module_var, path, "C")


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

    version, txt = tools.set_module_var(path, "__version__", "9.10.11")
    assert version == "6.7.8"
    assert (
        txt.rstrip()
        == """
# a fist comment line
__hash__ = "9.10.11"
# end of test
__version__ = "9.10.11"
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
    assert tools.get_module_var(repo.initfile, "__hash__") == GITHUB["master"]["sha"][:7]


def test_update_version_beta(git_project_factory):
    "test the update_version processing on the master branch"

    repo = git_project_factory().create("0.3.10")
    assert tools.get_module_var(repo.initfile) == "0.3.10"
    assert repo.branch() == "master"

    # branch
    repo.branch("beta/0.3.10", "master")
    assert repo.branch() == "beta/0.3.10"

    assert tools.update_version(repo.initfile, abort=False)
    assert tools.get_module_var(repo.initfile) == "0.3.10b0"
    assert (
        tools.get_module_var(repo.initfile, "__hash__")
        == repo(["rev-parse", "HEAD"])[:7]
    )
    repo.revert(repo.initfile)

    assert tools.get_module_var(repo.initfile) == "0.3.10"
    assert tools.update_version(repo.initfile, GITHUB["beta"], abort=False)
    assert tools.get_module_var(repo.initfile) == "0.3.10b98"
    assert tools.get_module_var(repo.initfile, "__hash__") == "507c657"
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
    repo = git_project_factory().create("0.3.9")
    assert tools.get_module_var(repo.initfile) == "0.3.9"

    # branch
    repo.branch("beta/0.3.9", "master")
    assert repo.branch() == "beta/0.3.9"

    path = repo.workdir / "hello.txt"
    path.write_text("hello world\n")
    repo.commit(path, "initial")

    repo(["tag", "release/0.3.9", repo(["rev-parse", "HEAD"])[:7]])

    assert (
        tools.update_version(repo.initfile, GITHUB["release"], abort=False) == "0.3.9"
    )
    assert tools.get_module_var(repo.initfile) == "0.3.9"
    assert tools.get_module_var(repo.initfile, "__hash__") == GITHUB["release"]["sha"][:7]
    repo.revert(repo.initfile)


def test_process(git_project_factory):

    # generate the project
    repo = git_project_factory().create("0.3.10")
    assert repo.initfile.read_text() == '__version__ = "0.3.10"\n'

    record = repo.initfile.parent / "_build.py"
    assert not record.exists()

    # we generate the build using a GITHUB_DUMP variable
    tools.process(repo.initfile, json.dumps(GITHUB["beta"]), record)

    assert repo.initfile.read_text() == f"""
__version__ = "0.3.10b98"
__hash__ = "{GITHUB['beta']['sha'][:7]}"
""".strip()

    assert record.read_text() == """
# autogenerate build file
branch = 'beta/0.3.10'
build = '98'
current = '0.3.10'
ref = 'refs/heads/beta/0.3.10'
runid = '5904313530'
sha = '507c657056d1a66520ec6b219a64706e70b0ff15'
version = '0.3.10b98'
workflow = 'beta'
""".lstrip()

    tools.process(repo.initfile, None, record)

def test_process_fixers(git_project_factory):
    def write_tfile(tfile):
        tfile.write_text(
            """
{% for k, v in ctx.items() | sort -%}
Key[{{k}}] = {{v}}
{% endfor %}
"""
        )
        return tfile

    repo = git_project_factory().create("1.2.3")

    # tfile won't appear in the repo.status() because is untracked
    tfile = write_tfile(repo.workdir / "test.txt")

    data = tools.process(repo.initfile, None, "_build.py", tfile)

    assert data["sha"][-1] != "*"

    assert (
        tfile.read_text()
        == f"""
Key[branch] = master
Key[build] = 0
Key[current] = 1.2.3
Key[ref] = {data['ref']}
Key[runid] = 0
Key[sha] = {data['sha']}
Key[version] = 1.2.3
Key[workflow] = master
"""
    )

    # clean and switch to new branch
    repo.revert(repo.initfile)
    (repo.initfile.parent / "_build.py").unlink()

    write_tfile(tfile)
    repo.branch("beta/1.2.3", "master")

    data = tools.process(repo.initfile, None, "_build.py", tfile)
    assert data["sha"][-1] != "*"

    assert (
        tfile.read_text()
        == f"""
Key[branch] = beta/1.2.3
Key[build] = 0
Key[current] = 1.2.3
Key[ref] = {data['ref']}
Key[runid] = 0
Key[sha] = {data['sha']}
Key[version] = 1.2.3b0
Key[workflow] = beta
"""
    )
