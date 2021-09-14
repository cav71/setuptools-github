import itertools
from setuptools.github import tools

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


def test_initversion(tmp_path):
    with open(tmp_path / "in.txt", "w") as fp:
        fp.write(
            """
# a test file
__version__ = "1.2.3"
__hash__ = "4.5.6"

# end of test
"""
        )
    version, txt = tools.initversion(tmp_path / "in.txt", "__version__", "6.7.8")
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
    version, txt = tools.initversion(tmp_path / "in.txt", "__hash__", "6.7.8")
    assert version == "4.5.6"
    assert (
        txt
        == """
# a test file
__version__ = "1.2.3"
__hash__ = "6.7.8"

# end of test
"""
    )

    tools.initversion(tmp_path / "in.txt", "__version__", "6.7.8", inplace=True)
    tools.initversion(tmp_path / "in.txt", "__hash__", "8.9.10", inplace=True)

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
    class M:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def writeinit():
        with open(tmp_path / "in.txt", "w") as fp:
            fp.write(
                """
# a test file
__version__ = "1.2.3"
__hash__ = "4.5.6"

# end of test
"""
            )

    writeinit()
    assert not tools.update_version(None, None)
    module = M(__file__=tmp_path / "in.txt", __version__="1.2.3")
    tools.update_version(GIT_DUMPS["master"], module)
    assert (
        (tmp_path / "in.txt").read_text()
        == """
# a test file
__version__ = "1.2.3"
__hash__ = "2169f90c"

# end of test
"""
    )

    writeinit()
    tools.update_version(GIT_DUMPS["beta"], module)
    assert (
        (tmp_path / "in.txt").read_text()
        == """
# a test file
__version__ = "0.0.4b8"
__hash__ = "2169f90c22e"

# end of test
"""
    )

    writeinit()
    tools.update_version(GIT_DUMPS["release"], module)
    assert (
        (tmp_path / "in.txt").read_text()
        == """
# a test file
__version__ = "0.0.3"
__hash__ = "5547365c82"

# end of test
"""
    )
