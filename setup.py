import re
import json

import os
import pathlib

from setuptools import setup, find_namespace_packages


def getversion(initfile):
    expr = re.compile("^__version__\\s*=\\s*['\\\"](?P<value>[^\\\"']+)['\\\"]")
    input_lines = initfile.read_text().split("\n")
    for line in reversed(input_lines):
        match = expr.search(line)
        if match:
            return match.group("value")


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


def update_version(data, path, fallback):
    if not data:
        return

    gdata = json.loads(data)
    version, thehash = hubversion(gdata, fallback)

    lines = pathlib.Path(path).read_text().split("\n")

    exp = re.compile(r"__version__\s*=\s*")
    exp1 = re.compile(r"__hash__\s*=\s*")
    assert len([l for l in lines if exp.search(l)]) == 1  # noqa: E741
    assert len([l for l in lines if exp1.search(l)]) == 1  # noqa: E741

    lines = [
        f'__version__ = "{version}"'
        if exp.search(l)
        else f'__hash__ = "{thehash}"'
        if exp1.search(l)
        else l
        for l in lines  # noqa: E741
    ]

    pathlib.Path(path).write_text("\n".join(lines))
    return version


initfile = pathlib.Path(__file__).parent / "src/setuptools_github/__init__.py"
version = update_version(os.getenv("GITHUB_DUMP"), initfile, getversion(initfile))

packages = find_namespace_packages(where="src")

setup(
    name="setuptools-github",
    version=version,
    url="https://github.com/cav71/setuptools-github",
    packages=packages,
    package_dir={"setuptools_github": "src/setuptools_github"},
    description="supports github releases",
    long_description=pathlib.Path("README.rst").read_text(),
    long_description_content_type="text/x-rst",
    install_requires=["setuptools"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
)
