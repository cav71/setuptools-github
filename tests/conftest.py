from __future__ import annotations

import os
import io
import re
import sys
import pathlib
import shutil
import contextlib
import collections
import subprocess
from typing import Union, Optional, Tuple, List, Dict, Any

import pytest


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


###################
# GIT TEST HELPER #
###################


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
    from pathlib import Path

    def indent(txt, pre=" " * 2):
        "simple text indentation"

        from textwrap import dedent

        txt = dedent(txt)
        if txt.endswith("\n"):
            last_eol = "\n"
            txt = txt[:-1]
        else:
            last_eol = ""

        result = pre + txt.replace("\n", "\n" + pre) + last_eol
        return result if result.strip() else ""

    class GitRepo:
        def __init__(
            self,
            workdir: Union[Path, str],
            identity: Tuple[str, str] = ("First Last", "user@email"),
            exe: Optional[str] = None,
            gitdir: Optional[Union[Path, str]] = None,
        ):
            self.workdir = Path(workdir).absolute()
            self.identity = identity
            self.exe = exe or "git"
            self.gitdir = (
                Path(gitdir) if gitdir else (self.workdir / ".git")
            ).absolute()

        def __call__(self, cmd: Union[List[Any], Any]) -> str:
            cmds = [cmd] if isinstance(cmd, str) else cmd

            arguments = [
                self.exe,
            ]
            if str(cmds[0]) != "clone":
                arguments.extend(
                    [
                        "--git-dir",
                        self.gitdir,
                        "--work-tree",
                        self.workdir,
                    ]
                )
            arguments.extend(cmds)
            return subprocess.check_output(
                [str(a) for a in arguments], encoding="utf-8"
            )

        def init(
            self,
            force: bool = False,
            identity: Optional[Tuple[str, str]] = None,
        ) -> GitRepo:
            from shutil import rmtree

            identity = self.identity if identity is None else identity
            keepfile = self.workdir / ".keep"

            if force:
                rmtree(self.workdir, ignore_errors=True)
            self.workdir.mkdir(parents=True, exist_ok=True if force else False)

            self(["init", "-b", "master"])

            self(["config", "init.defaultBranch", "master"])
            self(["config", "user.name", identity[0]])
            self(["config", "user.email", identity[1]])

            # need to create a commit to setup all refs
            keepfile.write_text("# dummy file to create the master branch")
            self(["add", keepfile])
            self(["commit", "-m", "initial", keepfile])

            return self

        def clone(
            self,
            dest: Union[str, Path],
            force=False,
            branch: Optional[str] = None,
        ) -> GitRepo:
            from shutil import rmtree

            workdir = Path(dest).absolute()
            if force:
                rmtree(workdir, ignore_errors=True)
            if workdir.exists():
                raise ValueError(f"target directory present {workdir}")

            self(
                [
                    "clone",
                    *(["--branch", branch] if branch else []),
                    self.workdir.absolute(),
                    workdir.absolute(),
                ],
            )

            return self.__class__(workdir=workdir, identity=self.identity, exe=self.exe)

        def __truediv__(self, other):
            return self.workdir.absolute() / other

        def dumps(self, mask=False) -> str:
            lines = f"REPO: {self.workdir}"
            lines += "\n [status]\n" + indent(self(["status"]))
            branches = self(["branch", "-avv"])
            if mask:
                branches = re.sub(r"(..\w\s+)\w{7}(\s+.*)", r"\1ABCDEFG\2", branches)
            lines += "\n [branch]\n" + indent(branches)
            lines += "\n [tags]\n" + indent(self(["tag", "-l"]))
            lines += "\n [remote]\n" + indent(self(["remote", "-v"]))

            buf = io.StringIO()
            print("\n".join([line.rstrip() for line in lines.split("\n")]), file=buf)
            return buf.getvalue()

    class GitCommand(GitRepo):
        BETA_BRANCHES = re.compile(r"/beta/(?P<ver>\d+([.]\d+)*)")

        def commit(
            self, paths: Union[str, Path, List[Union[str, Path]]], message: str
        ) -> None:
            paths = [paths] if isinstance(paths, (Path, str)) else paths
            self(["add", *paths])
            self(["commit", "-m", message, *paths])

        def branch(self, name: Optional[str] = None, origin: str = "master") -> str:
            if not name:
                return self(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
            assert origin or origin is None
            old = self.branch()
            self(["checkout", "-b", name, "--track", origin])
            return old

        def branches(
            self, expr: Optional[Union[str, bool, re.Pattern]] = None
        ) -> Tuple[List[str], Dict[str, List[str]]]:
            branches = self(["branch", "-a", "--format", "%(refname)"]).split()
            matchobj = re.compile(expr) if isinstance(expr, str) else expr

            if matchobj:
                branches = [name for name in branches if matchobj.search(name)]

            n = len("refs/heads/")
            local_branches = [
                name[n:] for name in branches if name.startswith("refs/heads/")
            ]
            remote_branches: Dict[str, List[str]] = {}
            n = len("refs/remotes/")
            for name in branches:
                if not name.startswith("refs/remotes/"):
                    continue
                origin, _, name = name[n:].partition("/")
                if origin not in remote_branches:
                    remote_branches[origin] = []
                remote_branches[origin].append(name)
            return local_branches, remote_branches

    class Project(GitCommand):
        @property
        def initfile(self):
            return self.workdir / "src" / "__init__.py"

        @property
        def version(self):
            return (
                self.initfile.read_text()
                .partition("=")[2]
                .strip()
                .replace("'", '"')
                .strip('"')
            )

        def create(self, version=None, clone=None, force=False):
            if clone:
                clone.clone(self.workdir, force=force)
            else:
                self.init(force=force)

            if version is not None:
                self.initfile.parent.mkdir(parents=True, exist_ok=True)
                self.initfile.write_text(
                    f"""
    __version__ = "{version}"
""".lstrip()
                )
                self.commit([self.initfile], "initial commit")
            return self

    def id_generator(size=6):
        from string import ascii_uppercase, digits
        from random import choice

        return "".join(choice(ascii_uppercase + digits) for _ in range(size))

    return lambda subdir="": Project(tmp_path / (subdir or id_generator()))
    # or request.node.name


def pytest_configure(config):
    config.addinivalue_line("markers", "manual: test intented to run manually")


def pytest_collection_modifyitems(config, items):
    if config.option.keyword or config.option.markexpr:
        return  # let pytest handle this

    for item in items:
        if "manual" not in item.keywords:
            continue
        item.add_marker(pytest.mark.skip(reason="manual not selected"))
