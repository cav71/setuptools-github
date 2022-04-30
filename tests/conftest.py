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

    class Project:
        def __init__(self, workdir, repo=None):
            self.workdir = workdir
            self.repo = repo

        @property
        def initfile(self):
            return self.workdir / "src" / "__init__.py"

        def create(self, version, workdir=None):
            from pygit2 import init_repository, Repository, Signature

            self.workdir = workdir or self.workdir

            init_repository(self.workdir)
            self.repo = repo = Repository(self.workdir)

            repo.config["user.name"] = "myusername"
            repo.config["user.email"] = "myemail"

            self.initfile.parent.mkdir(parents=True, exist_ok=True)
            self.initfile.write_text(
                f"""
    __version__ = "{version}"
""".lstrip()
            )

            repo.index.add(_2p(self.initfile.relative_to(self.workdir)))
            repo.index.write()

            sig = Signature("no-body", "a.b.c@example.com")
            repo.create_commit("HEAD", sig, sig, "hello", repo.index.write_tree(), [])
            return self

        @property
        def version(self):
            return self.initfile.read_text().partition("=")[2].strip().strip('"')

        @property
        def branch(self):
            return self.repo.head.shorthand

        def checkout(self, name):
            cur = self.branch
            ref = self.repo.lookup_reference(self.repo.lookup_branch(name).name)
            self.repo.checkout(ref)
            return cur

        @contextlib.contextmanager
        def in_branch(self, name):
            original = self.checkout(name)
            yield original
            self.checkout(original)

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
