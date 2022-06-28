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
from typing import Union, Optional, Tuple, TextIO, List, Dict, Any

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


@pytest.fixture(scope="function")
def git_project_factory(request, tmp_path):
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

        return pre + txt.replace("\n", "\n" + pre) + last_eol

    class GitWrapper:
        EXE: str = "git"
        KEEPFILE = ".keep"

        def __init__(
            self,
            workdir: Union[Path, str],
            exe: Optional[str] = None,
            identity: Tuple[str, str] = ("First Last", "user@email"),
        ):
            self.workdir = Path(workdir)
            self.exe = exe or self.EXE
            self.identity = identity

        def init(
            self,
            force: bool = False,
            keepfile: Optional[Union[bool, Path]] = True,
            identity: Optional[Tuple[str, str]] = None,
        ) -> GitWrapper:
            from shutil import rmtree

            identity = self.identity if identity is None else identity
            keepfile = self.workdir / self.KEEPFILE if keepfile is True else keepfile

            if force:
                rmtree(self.workdir, ignore_errors=True)
            self.workdir.mkdir(parents=True, exist_ok=True if force else False)
            self("init")

            if identity:
                self(["config", "user.name", identity[0]])
                self(["config", "user.email", identity[1]])

            if keepfile:
                keepfile.write_text("# dummy file to create the master branch")
                self(["add", keepfile])
                self(["commit", "-m", "initial", keepfile])
            return self

        def clone(
            self,
            dest: Union[str, Path],
            force=False,
            branch: Optional[str] = None,
            exe: Optional[str] = None,
            identity: Optional[Tuple[str, str]] = None,
        ) -> GitWrapper:
            from shutil import rmtree

            dest = Path(dest)
            identity = self.identity if identity is None else identity
            exe = self.exe if exe is None else exe

            if force:
                rmtree(dest, ignore_errors=True)
            else:
                if dest.exists():
                    raise ValueError(f"target directory present {dest}")

            self(
                [
                    "clone",
                    *(["--branch", branch] if branch else []),
                    self.workdir.absolute(),
                    dest.absolute(),
                ],
            )

            result = self.__class__(dest, exe=exe, identity=identity)
            if identity:
                result(["config", "user.name", identity[0]])
                result(["config", "user.email", identity[1]])
            return result

        def __call__(self, cmd: Union[List[Any], Any], *args) -> str:
            arguments = []
            if isinstance(cmd, str):
                arguments.append(cmd)
            else:
                arguments.extend(cmd[:])

            if str(arguments[0]) != "clone":
                arguments = [
                    self.exe,
                    "--git-dir",
                    str(self.workdir.absolute() / ".git"),
                    "--work-tree",
                    str(self.workdir.absolute()),
                    *[str(a) for a in arguments],
                ]
            else:
                arguments = [self.exe, *[str(a) for a in arguments]]
            return subprocess.check_output(arguments, encoding="utf-8")

        def __truediv__(self, other):
            return self.workdir.absolute() / other

        def dump(self, fp: TextIO = sys.stdout) -> Optional[str]:
            lines = f"REPO: {self.workdir}"
            lines += "\n [status]\n" + indent(self(["status"]))
            lines += "\n [branch]\n" + indent(self(["branch", "-avv"]))
            lines += "\n [tags]\n" + indent(self(["tag", "-l"]))
            lines += "\n [remote]\n" + indent(self(["remote", "-v"]))
            if fp == io.StringIO:
                buf = io.StringIO()
                print(lines, file=buf)
                return buf.getvalue()
            else:
                print(lines, file=fp)
                return None

    class GitCli(GitWrapper):
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

    class Project(GitCli):
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
            # repo = git_project_factory().create("0.0.0")
            # repo1 = git_project_factory().create(clone=repo)
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

    return lambda subdir="": Project(tmp_path / (subdir or request.node.name))


def pytest_configure(config):
    config.addinivalue_line("markers", "manual: test intented to run manually")


def pytest_collection_modifyitems(config, items):
    if config.option.keyword or config.option.markexpr:
        return  # let pytest handle this

    for item in items:
        if "manual" not in item.keywords:
            continue
        item.add_marker(pytest.mark.skip(reason="manual not selected"))
