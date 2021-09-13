import itertools
from setuptools.github import tools


def test_hubversion():
    testdata = [
        # test 1
        {
            "ref": "refs/heads/beta/0.0.4",
            "sha": "2169f90c22e",
            "run_number": "8",
        },
        {
            "ref": "refs/tags/release/0.0.3",
            "sha": "5547365c82",
            "run_number": "3",
        },
        {
            "ref": "refs/heads/master",
            "sha": "2169f90c",
            "run_number": "20",
        },
    ]

    fallbacks = [
        "123",
        "",
    ]

    expects = [
        ("0.0.4b8", "2169f90c22e"),
        ("0.0.4b8", "2169f90c22e"),
        ("0.0.3", "5547365c82"),
        ("0.0.3", "5547365c82"),
        ("123", "2169f90c"),
        ("", "2169f90c"),
    ]

    itrange = itertools.product(testdata, fallbacks)
    for index, (gdata, fallback) in enumerate(itrange):
        expected = expects[index]
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
