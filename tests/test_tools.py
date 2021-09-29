import pytest
import itertools
from setuptools_github import tools

GIT_DUMPS = {
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


def test_get_module_var(tmp_path):
    with open(tmp_path / "in.txt", "w") as fp:
        fp.write(
            """
# a test file
A = 12
B = 3+5
C = "hello"
# end of test
"""
        )
    assert 12 == tools.get_module_var(tmp_path / "in.txt", "A")
    assert "hello" == tools.get_module_var(tmp_path / "in.txt", "C")
    pytest.raises(AssertionError, tools.get_module_var, tmp_path / "in.txt", "B")


def test_hubversion():
    fallbacks = [
        "123",
        "",
    ]

    expects = {
        ("beta", ""): ("0.0.4b8", "2169f90c22e"),
        ("beta", "123"): ("0.0.4b8", "2169f90c22e"),
        ("release", "123"): ("0.0.3", "5547365c82"),
        ("release", ""): ("0.0.3", "5547365c82"),
        ("master", "123"): ("123", "2169f90c"),
        ("master", ""): ("", "2169f90c"),
    }

    itrange = itertools.product(GIT_DUMPS, fallbacks)
    for key, fallback in itrange:
        gdata = GIT_DUMPS[key]
        expected = expects[(key, fallback)]
        assert expected == tools.hubversion(gdata, fallback)


def test_set_module_var(tmp_path):

    with open(tmp_path / "in.txt", "w") as fp:
        fp.write(
            """
# a test file
__version__ = ""
__hash__ = "4.5.6"

# end of test
"""
        )
    version, txt = tools.set_module_var(tmp_path / "in.txt", "__version__", "6.7.8")
    assert not version
    assert (
        txt
        == """
# a test file
__version__ = "6.7.8"
__hash__ = "4.5.6"

# end of test
"""
    )

    with open(tmp_path / "in.txt", "w") as fp:
        fp.write(
            """
# a test file
__version__ = "1.2.3"
__hash__ = "4.5.6"

# end of test
"""
        )
    version, txt = tools.set_module_var(tmp_path / "in.txt", "__version__", "6.7.8")
    assert version == "1.2.3"
    assert (
        txt
        == """
# a test file
__version__ = "6.7.8"
__hash__ = "4.5.6"

# end of test
"""
    )
    version, txt = tools.set_module_var(tmp_path / "in.txt", "__hash__", "9.10.11")
    assert version == "4.5.6"
    assert (
        txt
        == """
# a test file
__version__ = "6.7.8"
__hash__ = "9.10.11"

# end of test
"""
    )
    return

    tools.set_module_var(tmp_path / "in.txt", "__version__", "6.7.8")
    tools.set_module_var(tmp_path / "in.txt", "__hash__", "8.9.10")

    assert (
        (tmp_path / "in.txt").read_text()
        == """
# a test file
__version__ = "6.7.8"
__hash__ = "8.9.10"

# end of test
"""
    )


def test_update_version(tmp_path):
    def writeinit(initfile):
        with open(initfile, "w") as fp:
            fp.write(
                """
# a test file
__version__ = "1.2.3"
__hash__ = "4.5.6"

# end of test
"""
            )

    initfile = tmp_path / "in.txt"
    writeinit(initfile)

    assert "1.2.3" == tools.update_version(initfile)

    tools.update_version(initfile, GIT_DUMPS["master"])
    assert (
        initfile.read_text()
        == """
# a test file
__version__ = "1.2.3"
__hash__ = "2169f90c"

# end of test
"""
    )

    writeinit(initfile)
    tools.update_version(initfile, GIT_DUMPS["beta"])
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
    tools.update_version(initfile, GIT_DUMPS["release"])
    assert (
        initfile.read_text()
        == """
# a test file
__version__ = "0.0.3"
__hash__ = "5547365c82"

# end of test
"""
    )
