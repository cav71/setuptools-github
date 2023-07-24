from __future__ import annotations

import os
import sys
import pathlib
import shutil
import contextlib
import collections
import subprocess

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from setuptools_github import scm  # noqa F401,E402


@pytest.fixture()
def datadir(request):
    basedir = pathlib.Path(__file__).parent / "data"
    if os.getenv("DATADIR"):
        basedir = pathlib.Path(os.getenv("DATADIR"))
    basedir = basedir / getattr(request.module, "DATADIR", "")
    return basedir


@pytest.fixture()
def scripter(request, tmp_path_factory, datadir):
    """handles script (cli) execution

    def test(scripter):
        script = scripter / "script-file.py"
        result = script.run(["--help"]) # this will execute:
                                        #   script-file.py --help
        assert result.out and result.err
    """
    Result = collections.namedtuple("R", "out,err,code")

    class ScripterError(Exception):
        pass

    class MissingItemError(ScripterError):
        pass

    class Exe:
        def __repr__(self):
            return (
                f"<{self.__class__.__name__} script={self.script} at {hex(id(self))}>"
            )

        def __init__(self, script, workdir, datadir, exe):
            self.script = script
            self.workdir = workdir
            self.datadir = datadir
            self.exe = exe
            if not pathlib.Path(script).exists():
                raise MissingItemError(f"script file {script} not found")

        def run(self, args, cwd=None, load_data=True):
            cmd = [str(a) for a in [self.exe, self.script, *args]]

            with contextlib.ExitStack() as stack:
                fpout = stack.enter_context((self.workdir / "stdout.txt").open("w"))
                fperr = stack.enter_context((self.workdir / "stderr.txt").open("w"))
                self.p = subprocess.Popen(
                    cmd,
                    cwd=self.workdir if cwd is True else cwd,
                    stdout=fpout,
                    stderr=fperr,
                )
                self.p.communicate()
            out = (self.workdir / "stdout.txt").read_text()
            err = (self.workdir / "stderr.txt").read_text()
            return Result(
                out.replace("\r\n", "\n"), err.replace("\r\n", "\n"), self.p.returncode
            )

        def compare(self, refdir, populate=False):
            src = self.datadir / refdir
            if not src.exists():
                raise MissingItemError(f"reference dir {src} not found")

            for name in ["stdout.txt", "stderr.txt"]:
                left = src / name
                right = self.workdir / name
                if populate:
                    if left.exists():
                        raise ScripterError(f"cannot overwrite {left} with {right}")
                    shutil.copyfile(right, left)
                assert left.read_text() == right.read_text()

    class Scripter:
        def __init__(self, srcdir, datadir, exe=sys.executable):
            self.srcdir = srcdir
            self.datadir = datadir
            self.exe = exe

        def __truediv__(self, path):
            tmpdir = tmp_path_factory.mktemp(pathlib.Path(path).with_suffix("").name)
            return Exe(self.srcdir / path, tmpdir, self.datadir, self.exe)

    return Scripter(pathlib.Path(request.module.__file__).parent, datadir)


@pytest.fixture(scope="function")
def git_project_factory(request, tmp_path):
    """fixture to generate git working repositories

    def test(git_project_factory):
        # simple git repo (only 1 .keep file)
        repo = git_project_factory().create()

        # git repo with a "version" src/__init__.py file
        repo1 = git_project_factory().create("0.0.0")

        # clone from repo
        repo2 = git_project_factory().create(clone=repo)

        assert repo.workdir != repo1.workdir
        assert repo.workdir != repo1.workdir

    """
    class GitRepoBase(scm.GitRepo):
        def init(
            self,
            force: bool = False,
            nobranch: bool = False
        ) -> GitRepoBase:
            from shutil import rmtree

            if force:
                rmtree(self.workdir, ignore_errors=True)
            self.workdir.mkdir(parents=True, exist_ok=True if force else False)

            if not nobranch:
                self(["init", "-b", "master"])
            else:
                self(["init",])

            self(["config", "user.name", "First Last"])
            self(["config", "user.email", "user@email"])

            if not nobranch:
                self(["commit", "-m", "initial", "--allow-empty"])
            return self

    class Project(GitRepoBase):
        @property
        def initfile(self):
            return self.workdir / "src" / "__init__.py"

        def version(self, value=None):
            if value is not None:
                initial = not self.initfile.exists()
                self.initfile.parent.mkdir(parents=True, exist_ok=True)
                self.initfile.write_text(f'__version__ = "{value}"\n')
                self.commit(
                    [self.initfile], "initial commit" if initial else "update version"
                )

            if not self.initfile.exists():
                return None

            lines = [
                line.partition("=")[2].strip().strip("'").strip('"')
                for line in self.initfile.read_text().split("\n")
                if line.strip().startswith("__version__")
            ]
            return lines[0] if lines else None

        def create(self, version=None, clone=None, force=False, nobranch=False):
            if clone:
                clone.clone(self.workdir, force=force)
            else:
                self.init(force=force, nobranch=nobranch)
            self.version(version)
            return self

    def id_generator(size=6):
        from string import ascii_uppercase, digits
        from random import choice

        return "".join(choice(ascii_uppercase + digits) for _ in range(size))

    return lambda subdir="": Project(tmp_path / (subdir or id_generator()))
    # or request.node.name

#####################
# Main flags/config #
#####################


def pytest_configure(config):
    config.addinivalue_line("markers", "manual: test intented to run manually")


def pytest_collection_modifyitems(config, items):
    if config.option.keyword or config.option.markexpr:
        return  # let pytest handle this

    for item in items:
        if "manual" not in item.keywords:
            continue
        item.add_marker(pytest.mark.skip(reason="manual not selected"))
