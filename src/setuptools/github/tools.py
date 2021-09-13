import os
import re


def hubversion(gdata, fallback):
    "extracts a (version, shasum) from a GITHUB_DUMP variable"

    def getversion(txt):
        return ".".join(str(int(v)) for v in txt.split("."))

    ref = gdata["ref"]  # eg. "refs/tags/release/0.0.3"
    number = gdata["run_number"]  # eg. 3
    shasum = gdata["sha"]  # eg. "2169f90c"

    if ref == "refs/heads/master":
        return (fallback, shasum)

    if ref.startswith("refs/heads/beta/"):
        version = getversion(ref.rpartition("/")[2])
        return (f"{version}b{number}", shasum)

    if ref.startswith("refs/tags/release/"):
        version = getversion(ref.rpartition("/")[2])
        return (f"{version}", shasum)

    raise RuntimeError("unhandled github ref", gdata)


def initversion(initfile, var, value, inplace=None):
    "fix the var with value (if not None)"
    # module level var
    expr = re.compile(f"^{var}\\s*=\\s*['\\\"](?P<value>[^\\\"']+)['\\\"]")
    fixed = None
    lines = []
    input_lines = initfile.read_text().split(os.linesep)
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
    txt = os.linesep.join(reversed(lines))
    if inplace:
        with initfile.open("w") as fp:
            fp.write(txt)
    return fixed, txt
