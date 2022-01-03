import re
import ast
import json

from pathlib import Path
from typing import Any, Union, Tuple


def get_module_var(
    initfile: Union[Path, str], key: str = "__version__", abort=True
) -> Any:
    "extracts from initfile the module level <key> variable"

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

    tree = ast.parse(Path(initfile).read_text())
    v = V({key})
    v.visit(tree)
    if key not in v.result and abort:
        raise RuntimeError(f"cannot find {key} in {initfile}")
    return v.result.get(key, None)


def set_module_var(initfile: Union[str, Path], var: str, value: Any) -> Tuple[Any, str]:
    """replace var in initfile with value

    Args:
        initfile (str,Path): init file containing var
        var (str): the variable to replace/extract
        value (None or Any): if not None replace var in initfile,
                                otherwise it will extract var

    Returns:
        (str, str) the previous var value, the new text
    """
    # module level var
    expr = re.compile(f"^{var}\\s*=\\s*['\\\"](?P<value>[^\\\"']*)['\\\"]")
    fixed = None
    lines = []
    input_lines = Path(initfile).read_text().split("\n")
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

    if value is not None:
        with Path(initfile).open("w") as fp:
            fp.write(txt)
    return fixed, txt


def hubversion(gdata, fallback: str) -> Tuple[str, str]:
    "extracts a (version, shasum) from a GITHUB_DUMP variable"

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

    raise RuntimeError("unhandled github ref", gdata)


def update_version(initfile: Union[str, Path], github_dump: Any = None) -> str:
    path = Path(initfile)

    if not github_dump:
        return get_module_var(path, "__version__")
    gdata = json.loads(github_dump) if isinstance(github_dump, str) else github_dump

    version, thehash = hubversion(gdata, get_module_var(path, "__version__"))
    set_module_var(path, "__version__", version)
    set_module_var(path, "__hash__", thehash)
    return version
