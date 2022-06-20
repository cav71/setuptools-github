#!/usr/bin/env python
# generates few git project to test conftest git_project_factory feature
import sys
from pathlib import Path
import subprocess
import argparse
import shutil


def indent(txt: str, pre: str = " " * 2) -> str:
    "simple text indentation"

    from textwrap import dedent

    txt = dedent(txt)
    if txt.endswith("\n"):
        last_eol = "\n"
        txt = txt[:-1]
    else:
        last_eol = ""

    return pre + txt.replace("\n", "\n" + pre) + last_eol


class Git:
    EXE = "git"

    def __init__(self, workdir, clone=None, exe=None):
        self.workdir = Path(workdir)
        self.clone = clone
        self.exe = exe or self.EXE

    def init(self):
        if self.clone:
            self(
                ["clone", self.clone.workdir.absolute(), self.workdir.absolute()],
            )
        else:
            self.workdir.mkdir(parents=True, exist_ok=True)
            self("init")
        return self

    def __call__(self, cmd):
        cmd = [cmd] if isinstance(cmd, str) else cmd[:]
        if cmd[0].startswith(">"):
            return getattr(self, cmd[0][1:])()
        cmd = [
            self.exe,
            *(
                []
                if cmd[0] == "clone"
                else [
                    "--git-dir",
                    self.workdir.absolute() / ".git",
                    "--work-tree",
                    self.workdir.absolute(),
                ]
            ),
            *cmd,
        ]
        txt = subprocess.check_output([str(c) for c in cmd], encoding="utf-8")
        return txt

    def __truediv__(self, other):
        return self.workdir.absolute() / other

    def dump(self):
        lines = f"REPO: {self.workdir}"
        lines += "\n [status]\n" + indent(self(["status"]))
        lines += "\n [branch]\n" + indent(self(["branch", "-avv"]))
        lines += "\n [remote]\n" + indent(self(["remote", "-v"]))
        lines += "\n [xdata]\n" + indent(self(">xdata"))
        print(lines)

    def xdata(self):
        header = [
            "name",
            "ref",
            "remote",
            "remote-ref",
            "upstream",
        ]
        cols = [
            "%(refname)",
            "%(objectname:short)",
            "%(upstream:remotename)",
            "%(upstream:remoteref)",
            "%(upstream:track)",
        ]
        assert len(header) == len(cols)
        return (
            " | ".join(header)
            + "\n"
            + self(["for-each-ref", "--format", " | ".join(cols)])
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-f", "--force", action="store_true")
    p.add_argument(
        "target", nargs="?", default=Path(__file__).with_suffix(""), type=Path
    )
    a = p.parse_args()

    dst = a.target
    if a.force:
        shutil.rmtree(dst, ignore_errors=True)

    if dst.exists():
        print(
            "directory {dst} present, remove before re-running this script",
            file=sys.stderr,
        )
        sys.exit()
    dst.mkdir(parents=True, exist_ok=True)

    # simple project with no remote
    git_no_remote = Git(dst / "no-remotes").init()

    # initial repo
    repo = Git(dst / "repo").init()
    path = repo / "hello.txt"
    path.write_text("hello world 1")
    repo(["add", path])
    repo(["commit", "-m", "initial", path])

    # cloned (1 remote)
    repo_clone_behind = Git(dst / "clone", repo).init()

    # repo with multiple remotes
    git_multi_remote = Git(dst / "multiple-remotes", repo).init()
    git_multi_remote(["remote", "add", "new-remote", repo_clone_behind.workdir])
    git_multi_remote(["fetch", "--all"])

    # update the original repo
    path = repo / "hello.txt"
    path.write_text("hello world 2")
    repo(["add", path])
    repo(["commit", "-m", "first change", path])

    git_multi_remote(["fetch", "--all"])
    repo.dump()
    git_multi_remote.dump()
