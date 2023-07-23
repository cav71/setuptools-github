from __future__ import annotations

import dataclasses as dc
import subprocess
from typing import TypeAlias, Union
from pathlib import Path


ListOfArgs: TypeAlias = Union[str | Path | list[str | Path]]


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


class GitRepo:
    def __init__(self, workdir: Path | str, exe: str = "git"):
        self.workdir = Path(workdir).absolute()
        self.exe = exe

    def __call__(self, cmd: ListOfArgs) -> str:
        cmds = cmd if isinstance(cmd, list) else [cmd]
        arguments = [
            self.exe,
            "--work-tree",
            str(self.workdir),
            "--git-dir",
            str(self.workdir / ".git"),
            *(str(c) for c in cmds),
        ]
        return subprocess.check_output(arguments, encoding="utf-8")

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

    @property
    def head(self):
        name = "refs/heads/master"
        txt = self(["rev-parse", name])
        return GitRepoHead(name=name, target=GitRepoHead.GitRepoHeadHex(txt.strip()))

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
