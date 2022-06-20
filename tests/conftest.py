import os
import sys
import pathlib
import shutil
import contextlib
import collections
import subprocess
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
def git_project_factory(tmp_path):
    # on windows we need to add paths with / separator
    def _2p(path):
        return str(path).replace("\\", "/")

    def indent(txt, pre=" " * 2):
        from textwrap import dedent

        txt = dedent(txt)
        if txt.endswith("\n"):
            last_eol = "\n"
            txt = txt[:-1]
        else:
            last_eol = ""

        return pre + txt.replace("\n", "\n" + pre) + last_eol

    class Project:
        def debug(self, *args):
            if args in {tuple(), ("all",)}:
                cmds = [
                    [
                        "status",
                    ],
                    [
                        "branch",
                        "-av",
                    ],
                    [
                        "remote",
                        "-v",
                    ],
                    [
                        "log",
                    ],
                ]
            else:
                cmds = [[str(a) for a in args]]
            lines = f"REPO: {self.workdir}"
            for cmd in cmds:
                out = subprocess.check_output(
                    ["git", *cmd], cwd=self.workdir, encoding="utf-8"
                )
                lines += f"\n [{cmd[0]}]\n" + indent(out)
            print(lines)

        def __init__(self, workdir, repo=None, sig=None):
            self.workdir = workdir
            self.repo = repo
            self.sig = sig

        @property
        def initfile(self):
            return self.workdir / "src" / "__init__.py"

        @property
        def version(self):
            return self.initfile.read_text().partition("=")[2].strip().strip('"')

        @property
        def branch(self):
            return self.repo.head

        def commit(self, paths, message):
            from pathlib import Path
            from pygit2 import GitError

            ref = "HEAD"
            with contextlib.suppress(GitError):
                ref = self.repo.head.name
            parents = []
            with contextlib.suppress(GitError):
                parents = [self.repo.head.target]
            index = self.repo.index
            for path in [Path(paths)] if isinstance(paths, (str, Path)) else paths:
                index.add(_2p(path.relative_to(self.workdir)))
            index.write()
            return self.repo.create_commit(
                ref, self.sig, self.sig, message, index.write_tree(), parents
            )

        def create_from_existing(self):
            from pygit2 import Repository, Signature

            self.repo = repo = Repository(self.workdir)
            repo.config["user.name"] = "myusername"
            repo.config["user.email"] = "myemail"

            if not self.sig:
                self.sig = Signature(
                    repo.config["user.name"], repo.config["user.email"]
                )
            return self

        def create(self, version, workdir=None, force=False, remote=True):
            from shutil import rmtree
            from pygit2 import init_repository, Repository, Signature

            self.workdir = workdir or self.workdir
            if force:
                rmtree(self.workdir, ignore_errors=True)

            init_repository(self.workdir)
            self.create_from_existing()

            if remote:
                self.repo.remotes.create(
                    *(("origin", "no-url", "origin") if remote is True else remote)
                )

            if version is not None:
                self.initfile.parent.mkdir(parents=True, exist_ok=True)
                self.initfile.write_text(
                    f"""
    __version__ = "{version}"
""".lstrip()
                )
                self.commit([self.initfile], "initial commit")
            return self

        def create_branch(self, name, commit=None, remote=False, exist_ok=False):
            commit = commit or self.repo.get(self.repo.head.target)
            target = self.repo.branches.remote if remote else self.repo.branches.local
            if name in target and exist_ok:
                branch = target[name]
            else:
                if remote:
                    self.repo.remotes.create(
                        name, "no-url" if remote is True else remote
                    )
                    return self.repo.references.create(
                        f"refs/remotes/{name}", commit.oid
                    )
                branch = target.create(name, commit)
            return branch

        def create_remote(self, name, url="invalid-url"):
            self.create_branch(f"origin/{name}", remote=url)

        def checkout(self, *, branch=None, exist_ok=False):
            if branch:
                branch_object = self.create_branch(branch, exist_ok=exist_ok)
                self.repo.checkout(branch_object)
            else:
                raise NotImplementedError("operation not implemented")

        def tag(self, name, ref=None):
            head = ref or self.repo.head
            return self.repo.references.create(
                f"refs/tags/{name.lstrip('/')}", head.target
            )

    return lambda subdir: Project(tmp_path / subdir)


def pytest_configure(config):
    config.addinivalue_line("markers", "manual: test intented to run manually")


def pytest_collection_modifyitems(config, items):
    if config.option.keyword or config.option.markexpr:
        return  # let pytest handle this

    for item in items:
        if "manual" not in item.keywords:
            continue
        item.add_marker(pytest.mark.skip(reason="manual not selected"))
