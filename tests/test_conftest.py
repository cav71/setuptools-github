from pathlib import Path
import functools
import pytest

DATADIR = Path(__file__).parent / "data" / "create-git-projects"


def skip_cond(fn):
    @functools.wraps(fn)
    def _fn(*args, **kwargs):
        return fn(*args, **kwargs)

    script = DATADIR.with_suffix(".py")

    if not DATADIR.exists():
        return pytest.mark.skipif(True, reason=f"{DATADIR} not present, run {script}")(
            _fn
        )
    return _fn


@skip_cond
def test_multiple_remote(git_project_factory):
    project = git_project_factory(DATADIR / "multiple-remotes").create_from_existing()
    assert {remote.name for remote in project.repo.remotes} == {"origin", "new-remote"}
    project.create_remote("blha", "no-url")
    project.debug()
