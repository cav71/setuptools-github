import contextlib
from unittest import mock

from setuptools_github import cli


def test_exception():
    obj = cli.AbortExecutionError(
        message="this is a short one-liner",
        explain="""
          It looks the repository doesn't have any branch,
          you should:
            git checkout --orphan <branch-name>
          """,
        hint="create a git branch",
    )
    assert str(obj) == """\
this is a short one-liner
reason:

  It looks the repository doesn't have any branch,
  you should:
    git checkout --orphan <branch-name>

hint:
  create a git branch\
"""


def test_docstring():
    @cli.cli()
    def hello(options):
        "this is a docstring"
        pass

    assert hello.__doc__ == "this is a docstring"


def test_cli_call_help():
    @cli.cli()
    def hello(options):
        pass

    with contextlib.ExitStack() as stack:
        def xxx(self, parser, namespace, values, option_string=None):
            assert parser.format_help().strip().replace(" py.test ", "pytest") == """
usage: pytest [-h] [-n] [-v]

options:
  -h, --help     show this help message and exit
  -n, --dry-run
  -v, --verbose
""".strip()
        stack.enter_context(mock.patch("argparse._HelpAction.__call__", new=xxx))
        hello(["--help"])

