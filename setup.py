import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
from setuptools_github import tools  # noqa E402
from setuptools import setup, find_namespace_packages  # noqa E402


fixers = {
    # for the github actions
    "/actions/workflows/master.yml/badge.svg": "/actions/workflows/{{ ctx.workflow }}.yml/badge.svg",  # noqa: E501
    "/actions/workflows/master.yml": "/actions/runs/{{ ctx.runid }}",
    # for the codecov part
    "/tree/master/graph/badge.svg?token=SIUMZ7MT5T": "/tree/{{ ctx.branch|urlquote }}/graph/badge.svg?token=SIUMZ7MT5T",  # noqa: E501
    "/tree/master": "/tree/{{ ctx.branch|urlquote }}",
}
initfile = pathlib.Path(__file__).parent / "src/setuptools_github/__init__.py"
readme = pathlib.Path(__file__).parent / "README.md"
version = tools.process(initfile, os.getenv("GITHUB_DUMP"), readme, fixers=fixers)[
    "version"
]

packages = find_namespace_packages(where="src")

setup(
    name="setuptools-github",
    version=version,
    url="https://github.com/cav71/setuptools-github",
    packages=packages,
    package_dir={"setuptools_github": "src/setuptools_github"},
    description="supports github releases",
    long_description=readme.read_text(),
    long_description_content_type="text/markdown",
    install_requires=[
        "setuptools",
        "typing-extensions",
        "jinja2",
    ],
    entry_points={
        "console_scripts": [
            "setuptools-github=setuptools_github.script:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
    ],
)
