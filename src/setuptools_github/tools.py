import re
import ast
import json

from pathlib import Path
from typing import Any, Union, Tuple, Optional


class GithubError(Exception):
    pass


class MissingVariable(GithubError):
    pass


class InvalidGithubReference(GithubError):
    pass


def get_module_var(
    path: Union[Path, str], var: str = "__version__", abort=True
) -> Optional[str]:
    """extracts from <filename> the module level <var> variable

    Args:
        path (str,Path): python module file to parse
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

    tree = ast.parse(Path(path).read_text())
    v = V({var})
    v.visit(tree)
    if var not in v.result and abort:
        raise MissingVariable(f"cannot find {var} in {path}", path, var)
    return v.result.get(var, None)


def set_module_var(path: Union[str, Path], var: str, value: Any) -> Tuple[Any, str]:
    """replace var in path with value

    Args:
        path (str,Path): python module file to parse
        var (str): module level variable name to extract
        value (None or Any): if not None replace var in initfile

    Returns:
        (str, str) the (<previous-var-value|None>, <the new text>)
    """
    # module level var
    expr = re.compile(f"^{var}\\s*=\\s*['\\\"](?P<value>[^\\\"']*)['\\\"]")
    fixed = None
    lines = []
    input_lines = Path(path).read_text().split("\n")
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

    with Path(path).open("w") as fp:
        fp.write(txt)
    return fixed, txt


def hubversion(gdata: Any, fallback: Optional[str]) -> Tuple[Optional[str], str]:
    """extracts a (version, shasum) from a GITHUB_DUMP variable

    Args:
        gdata: json dictionary from GITHUB_DUMP
        fallback: if a version is not defined in gdata uses fallback

    Returns:
        (str, str): <update-version>, <shasum>
    """

    def validate(txt):
        return ".".join(str(int(v)) for v in txt.split("."))

    ref = gdata["ref"]  # eg. "refs/tags/release/0.0.3"
    number = gdata["run_number"]  # eg. 3
    shasum = gdata["sha"]  # eg. "2169f90c"

    # the logic is:

    # if we are on master we fallback (likely to the version in the __init__.py module)
    if ref == "refs/heads/master":
        return (fallback, shasum)

    # on a beta branch we add a "b<build-number>" string to the __init__.py version
    # the bersion is taken from the refs/heads/beta/<version>
    if ref.startswith("refs/heads/beta/"):
        version = validate(ref.rpartition("/")[2])
        return (f"{version}b{number}", shasum)

    # on a release we use the version from the refs/tags/release/<version>
    if ref.startswith("refs/tags/release/"):
        version = validate(ref.rpartition("/")[2])
        return (f"{version}", shasum)

    raise InvalidGithubReference("unhandled github ref", gdata)


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
