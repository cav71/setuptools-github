import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
from setuptools_github import tools  # noqa E402
from setuptools import setup, find_namespace_packages  # noqa E402


PROOT = pathlib.Path(__file__).parent


GDATA = tools.process(
    # versionfile containing the __version__ / __hash__ module variables
    # (they will be update during build)
    version_file=PROOT / "src/setuptools_github/__init__.py",

    # this is the github environ (the output of ${{ toJson(github) }})
    # (see .github/workflows/master.yml)
    github_dump=os.getenv("GITHUB_DUMP"),

    # a list of files, processed using jinja2
    # fixers will replace text in `paths
    paths=[
        PROOT / "README.md",
    ],
    # fixers replacements are key:value pairs.
    # key might be a literal string (replaced with value) or a
    # string starting with `re:`, in that case key and value are
    # regular expression arguments to `re.sub`.
    # value are jinja2 processed with a ctx context having:
    #   ctx.__dict__ == {
    #       'branch': 'master',  <- current branch
    #       'build': 123,        <- build no. (github)
    #       'current': '0.3.7',  <- current version
    #       'hash': '13526de2b08fe3684cda35adf219f855cb4deadb',  <- commit hash
    #       'runid': 456,        <- workflow uid run (github)
    #       'version': '0.3.7',  <- package version (eg. 0.3.7b<build>
    #                                                for beta/0.3.7 branch)
    #       'workflow': 'master' <- workflow name (github)
    #   }
    fixers={
        # for the github actions
        "re:(https://github.com/.+/actions/workflows/)(master)(.yml/badge.svg)": (
            "\\1{{ ctx.workflow }}\\3"
        ),
        "re:(https://github.com/.+/actions)/(workflows/)(master.yml)(?!/)": (
            "\\1/runs/{{ ctx.runid }}"
        ),
        # for the codecov part
        "re:(https://codecov.io/gh/.+/tree)/master(/graph/badge.svg[?]token=.+)": (
            "\\1/{{ ctx.branch|urlquote }}\\2"
        ),
        "re:(https://codecov.io/gh/.+/tree)/master(?!/)": (
            "\\1/{{ ctx.branch|urlquote }}"
        ),
    },
)


setup(
    name="setuptools-github",
    version=GDATA["version"],
    url="https://github.com/cav71/setuptools-github",
    packages=find_namespace_packages(where="src"),
    package_dir={"setuptools_github": "src/setuptools_github"},
    description="supports github releases",
    long_description=(PROOT / "README.md").read_text(),
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
