import re
import ast
import json

from pathlib import Path
from typing import Any, Union, Tuple, Optional, List


class GithubError(Exception):
    pass


class MissingVariable(GithubError):
    pass


class InvalidGithubReference(GithubError):
    pass


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
    else:
        newver[-1] += 1
    return ".".join(str(v) for v in newver)


def extract_beta_branches(branches: List[str], remote: Optional[str] = None):
    result = set()
    for branch in branches:
        match = branch.partition("/")[0]
        if remote and remote != match:
            continue
        if re.search(r"beta/\d+([.]\d+)*", branch):
            result.add(branch)
    return result
