import pygit2  # type: ignore

from setuptools_github import start_release as sr


def test_newversion():
    assert "0.0.2" == sr.newversion("0.0.1", "micro")
    assert "0.0.3" == sr.newversion("0.0.2", "micro")

    assert "0.1.0" == sr.newversion("0.0.2", "minor")

    assert "2.0.0" == sr.newversion("1.2.3", "major")


def test_end2end():
    from pathlib import Path

    tmp_path = Path("out").absolute()

    def create_new_project(dst):
        pygit2.init_repository(dst)
        repo = pygit2.Repository(dst)

        (dst / "src").mkdir(parents=True, exist_ok=True)
        (dst / "src" / "__init__.py").write_text(
            """
__version__ = "0.0.3"
""".lstrip()
        )

        repo.index.add("src/__init__.py")
        tree = repo.index.write_tree()

        sig = pygit2.Signature("no-body", "a.b.c@example.com")
        repo.create_commit("HEAD", sig, sig, "hello", tree, [])

        return repo

    repo = create_new_project(tmp_path / "project")

    assert "master" == repo.head.shorthand
    assert (
        '__version__ = "0.0.3"'
        == (tmp_path / "project/src/__init__.py").read_text().strip()
    )

    args = [
        "-w",
        tmp_path / "project",
        "minor",
        tmp_path / "project/src/__init__.py",
        "--no-checks",
    ]
    kwargs = sr.parse_args([str(a) for a in args])
    sr.run(**kwargs)

    assert "beta/0.1.0" == repo.head.shorthand
    assert (
        '__version__ = "0.1.0"'
        == (tmp_path / "project/src/__init__.py").read_text().strip()
    )

    repo.checkout("refs/heads/master")
    assert "master" == repo.head.shorthand
    assert (
        '__version__ = "0.1.0"'
        == (tmp_path / "project/src/__init__.py").read_text().strip()
    )
