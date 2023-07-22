from setuptools_github import cli


def test_exception():
    obj = cli.AbortExecution(
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
