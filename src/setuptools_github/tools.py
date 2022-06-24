import re
import ast
import json
import subprocess

from pathlib import Path
from typing import Any, Union, Tuple, Optional, List


class GithubError(Exception):
    pass


class MissingVariable(GithubError):
    pass


class InvalidGithubReference(GithubError):
    pass


class AbortExecution(Exception):
    @staticmethod
    def _strip(txt):
        txt = txt or ""
        txt = txt[1:] if txt.startswith("\n") else txt
        txt = indent(txt, pre="")
        return txt[:-1] if txt.endswith("\n") else txt

    def __init__(
        self, message: str, explain: Optional[str] = None, hint: Optional[str] = None
    ):
        self.message = message.strip()
        self._explain = explain
        self._hint = hint

    @property
    def explain(self):
        return self._strip(self._explain)

    @property
    def hint(self):
        return self._strip(self._hint)

    def __str__(self):
        result = [self.message]
        if self.explain:
            result.append(indent("\n" + self.explain, pre=" " * 2)[2:])
        if self.hint:
            result.extend(["\nhint:", indent("\n" + self.hint, pre=" " * 2)[2:]])
        return "".join(result)


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


def hubversion(gdata: Any, fallback: Optional[str]) -> Tuple[Optional[str], str]:
    """gets a (version, sha) tuple from gdata.

    GITHUB_DUMP is a json dump of the environment during an action run and
    we pull the ref, run_number and sha keys.

    ref can be something like refs/heads/master for the master branch,
    refs/heads/beta/0.0.4 for a beta branch or refs/tags/release/0.0.3 for
    a release tag.

    the version returned is:
        ("", "<sha-value>") for the master branch
        ("0.0.4b8", "<sha-value>") for a beta branch (<version>b<build-number>)
        ("0.0.3", "<sha-value>") for the release

    Args:
        gdata: json dictionary from $GITHUB_DUMP
        fallback: returns this if a version is not defined in gdata

    Returns:
        (str, str): <update-version>, <shasum>
    """

    def validate(txt):
        return ".".join(str(int(v)) for v in txt.split("."))

    ref = gdata["ref"]  # eg. "refs/tags/release/0.0.3"
    number = gdata["run_number"]  # eg. 3
    shasum = gdata["sha"]  # eg. "2169f90c"

    # the logic for the returned version:

    # 1. if we are on master we use the version from the __init__.py module
    if ref == "refs/heads/master":
        return (fallback, shasum)

    # 2. on a beta branch we add a "b<build-number>" string to the __init__.py version
    #    the bersion is taken from the refs/heads/beta/<version>
    if ref.startswith("refs/heads/beta/"):
        version = validate(ref.rpartition("/")[2])
        return (f"{version}b{number}", shasum)

    # 3. on a release we use the version from the refs/tags/release/<version>
    if ref.startswith("refs/tags/release/"):
        version = validate(ref.rpartition("/")[2])
        return (f"{version}", shasum)

    raise InvalidGithubReference("unhandled github ref", gdata)


def get_module_var(
    path: Union[Path, str], var: str = "__version__", abort=True
) -> Optional[str]:
    """extract from a python module in path the module level <var> variable

    Args:
        path (str,Path): python module file to parse using ast (no code-execution)
        var (str): module level variable name to extract
        abort (bool): raise MissingVariable if var is not present

    Returns:
        None or str: the variable value if found or None

    Raises:
        MissingVariable: if the var is not found and abort is True

    Notes:
        this uses ast to parse path, so it doesn't load the module
    """

    class V(ast.NodeVisitor):
        def __init__(self, keys):
            self.keys = keys
            self.result = {}

        def visit_Module(self, node):
            # we extract the module level variables
            for subnode in ast.iter_child_nodes(node):
                if not isinstance(subnode, ast.Assign):
                    continue
                for target in subnode.targets:
                    if target.id not in self.keys:
                        continue
                    assert isinstance(
                        subnode.value, (ast.Num, ast.Str, ast.Constant)
                    ), (
                        f"cannot extract non Constant variable "
                        f"{target.id} ({type(subnode.value)})"
                    )
                    if isinstance(subnode.value, ast.Str):
                        value = subnode.value.s
                    elif isinstance(subnode.value, ast.Num):
                        value = subnode.value.n
                    else:
                        value = subnode.value.value
                    self.result[target.id] = value
            return self.generic_visit(node)

    v = V({var})
    path = Path(path)
    if path.exists():
        tree = ast.parse(Path(path).read_text())
        v.visit(tree)
    if var not in v.result and abort:
        raise MissingVariable(f"cannot find {var} in {path}", path, var)
    return v.result.get(var, None)


def set_module_var(
    path: Union[str, Path], var: str, value: Any, create: bool = True
) -> Tuple[Any, str]:
    """replace var in path with value

    Args:
        path (str,Path): python module file to parse
        var (str): module level variable name to extract
        value (None or Any): if not None replace var in initfile
        create (bool): create path if not present

    Returns:
        (str, str) the (<previous-var-value|None>, <the new text>)
    """
    # module level var
    expr = re.compile(f"^{var}\\s*=\\s*['\\\"](?P<value>[^\\\"']*)['\\\"]")
    fixed = None
    lines = []

    src = Path(path)
    if not src.exists() and create:
        src.parent.mkdir(parents=True, exist_ok=True)
        src.touch()

    input_lines = src.read_text().split("\n")
    for line in reversed(input_lines):
        if fixed:
            lines.append(line)
            continue
        match = expr.search(line)
        if match:
            fixed = match.group("value")
            if value is not None:
                x, y = match.span(1)
                line = line[:x] + value + line[y:]
        lines.append(line)
    txt = "\n".join(reversed(lines))
    if not fixed and create:
        if txt and txt[-1] != "\n":
            txt += "\n"
        txt += f'{var} = "{value}"'

    with Path(path).open("w") as fp:
        fp.write(txt)
    return fixed, txt


def update_version(
    initfile: Union[str, Path], github_dump: Optional[str] = None
) -> Optional[str]:
    """extracts version information from github_dump and updates initfile in-place

    Args:
        initfile (str, Path): path to the __init__.py file with a __version__ variable
        github_dump (str): the os.getenv("GITHUB_DUMP") value

    Returns:
        str: the new version for the package
    """

    path = Path(initfile)

    if not github_dump:
        return get_module_var(path, "__version__")
    gdata = json.loads(github_dump) if isinstance(github_dump, str) else github_dump

    version, thehash = hubversion(gdata, get_module_var(path, "__version__"))
    set_module_var(path, "__version__", version)
    set_module_var(path, "__hash__", thehash)
    return version


def bump_version(version: str, mode: str) -> str:
    """given a version str will bump it according to mode

    Arguments:
        version: text in the N.M.O form
        mode: major, minor or micro

    Returns:
        increased text

    >>> bump_version("1.0.3", "micro")
    "1.0.4"
    >>> bump_version("1.0.3", "minor")
    "1.1.0"
    """
    newver = [int(n) for n in version.split(".")]
    if mode == "major":
        newver[-3] += 1
        newver[-2] = 0
        newver[-1] = 0
    elif mode == "minor":
        newver[-2] += 1
        newver[-1] = 0
    elif mode == "micro":
        newver[-1] += 1
    return ".".join(str(v) for v in newver)


class GitWrapper:
    EXE: str = "git"
    KEEPFILE = ".keep"

    def __init__(self, workdir: Union[Path, str], exe: Optional[str] = None):
        self.workdir = Path(workdir)
        self.exe = exe or self.EXE

    def init(self, clone=None, force=False, keepfile=True):
        from shutil import rmtree

        assert isinstance(clone, (type(None), GitWrapper))

        if force:
            rmtree(self.workdir, ignore_errors=True)

        if clone:
            self(
                ["clone", clone.workdir.absolute(), self.workdir.absolute()],
            )
        else:
            self.workdir.mkdir(parents=True, exist_ok=True)
            self("init")
            self(["config", "user.name", "a user name"])
            self(["config", "user.email", "user@email"])
            if keepfile is True:
                keepfile = self.workdir / self.KEEPFILE
            if keepfile:
                keepfile.write_text("# dummy file to create the master branch")
                self(["add", keepfile])
                self(["commit", "-m", "initial", keepfile])
        return self

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

    def dump(self):
        lines = f"REPO: {self.workdir}"
        lines += "\n [status]\n" + indent(self(["status"]))
        lines += "\n [branch]\n" + indent(self(["branch", "-avv"]))
        lines += "\n [tags]\n" + indent(self(["tag", "-l"]))
        lines += "\n [remote]\n" + indent(self(["remote", "-v"]))
        print(lines)
