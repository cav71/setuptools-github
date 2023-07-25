from __future__ import annotations
import io
import re
import dataclasses as dc
import subprocess
from pathlib import Path


from typing_extensions import TypeAlias
from typing import Union, List


ListOfArgs: TypeAlias = Union[str, Path, List[Union[str, Path]]]


def to_list_of_paths(paths: ListOfArgs) -> list[Path]:
    return [Path(s) for s in ([paths] if isinstance(paths, (str, Path)) else paths)]


@dc.dataclass
class GitRepoBranches:
    local: list[str]
    remote: list[str]


@dc.dataclass
class GitRepoHead:
    @dc.dataclass
    class GitRepoHeadHex:
        hex: str

    name: str
    target: GitRepoHeadHex


class GitRepoBase:
    def __init__(self, workdir: Path | str, exe: str = "git", gitdir: Path | str = ""):
        self.workdir = Path(workdir).absolute()
        self.exe = exe
        self.gitdir = Path(gitdir or (self.workdir / ".git")).absolute()

    def __call__(self, cmd: ListOfArgs) -> str:
        cmds = cmd if isinstance(cmd, list) else [cmd]

        arguments = [self.exe]
        if cmds[0] != "clone":
            arguments.extend(
                [
                    "--work-tree",
                    str(self.workdir),
                    "--git-dir",
                    str(self.gitdir),
                ]
            )
        arguments.extend(str(c) for c in cmds)
        return subprocess.check_output(arguments, encoding="utf-8")

    def __truediv__(self, other):
        return (self.workdir / other).absolute()

    def dumps(self, mask=False) -> str:
        from setuptools_github.tools import indent

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


class GitRepo(GitRepoBase):
    # COMMANDS FOR THE REPO HERE
    def revert(self, paths: ListOfArgs | None = None):
        sources = to_list_of_paths(paths or self.workdir)
        self(["checkout", *sources])

    @property
    def head(self):
        name = self(["symbolic-ref", "HEAD"]).strip()
        txt = self(["rev-parse", name]).strip()
        return GitRepoHead(name=name, target=GitRepoHead.GitRepoHeadHex(txt))

    def status(
        self, untracked_files: str = "all", ignored: bool = False
    ) -> dict[str, int]:
        mapper = {
            "??": 128 if untracked_files == "all" else None,
            " D": 512,
            " M": 256,
        }
        result = {}
        for line in self(["status", "--porcelain"]).split("\n"):
            if not line.strip():
                continue
            tag, filename = line[:2], line[3:]
            value = mapper[tag]
            if value:
                result[filename] = value
        return result

    def commit(
        self,
        paths: ListOfArgs,
        message: str,
    ) -> None:
        all_paths = to_list_of_paths(paths)
        self(["add", *all_paths])
        self(["commit", "-m", message, *all_paths])

    def branch(self, name: str | None = None, origin: str = "master") -> str:
        if not name:
            name = self.head.name or ""
            return name[11:] if name.startswith("refs/heads/") else name
        assert origin or origin is None
        old = self.branch()
        self(["checkout", "-b", name, "--track", origin])
        return old[11:] if old.startswith("refs/heads/") else old

    @property
    def branches(self) -> GitRepoBranches:
        result = GitRepoBranches([], [])
        for line in self(["branch", "-a", "--format", "%(refname)"]).split("\n"):
            if not line.strip():
                continue
            if line.startswith("refs/heads/"):
                result.local.append(line[11:])
            elif line.startswith("refs/remotes/"):
                result.remote.append(line[13:])
            else:
                raise RuntimeError(f"invalid branch {line}")
        return result

    @property
    def references(self) -> list[str]:
        return [
            f"refs/tags/{line.strip()}"
            for line in self(["tag", "-l"]).split("\n")
            if line.strip()
        ]

    def clone(
        self,
        dest: str | Path,
        force=False,
        branch: str | None = None,
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

        repo = self.__class__(workdir=workdir)
        repo(["config", "user.name", self(["config", "user.name"])])
        repo(["config", "user.email", self(["config", "user.email"])])

        return repo


def lookup(path: Path) -> GitRepo | None:
    cur = path
    found = False
    while not found:
        if (cur / ".git").exists():
            return GitRepo(cur)
        if str(cur) == cur.root:
            break
        cur = cur.parent
    return None
