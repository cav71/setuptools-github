# setuptools-github

[![PyPI version](https://img.shields.io/pypi/v/setuptools-github.svg?color=blue)](https://pypi.org/project/setuptools-github)
[![Python versions](https://img.shields.io/pypi/pyversions/setuptools-github.svg)](https://pypi.org/project/setuptools-github)
[![License](https://img.shields.io/badge/License-BSD_2--Clause-blue.svg)](https://opensource.org/licenses/BSD-2-Clause)

[![Build](https://github.com/cav71/setuptools-github/actions/workflows/master.yml/badge.svg)](https://github.com/cav71/setuptools-github/actions/workflows/master.yml)
[![Codecov](https://codecov.io/gh/cav71/setuptools-github/tree/master/graph/badge.svg?token=SIUMZ7MT5T)](https://codecov.io/gh/cav71/setuptools-github/tree/master)

[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](Black)
[![Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)


## Introduction
setuptools-github helps to setup a simple project life cycle
where the target is delivering packages into [PyPI](https://pypi.org) from a hosted project at
[Github](https://www.gitgub.com). 

The idea is rather simple (and detailed in [here](https://cavallinux.org/projects/branched-based-deployment/index.html)):
- commits on a master branch will trigger code checks (static checks, tests etc.)
- commits on a `beta/N.M.O` branch will do all the previous checks + publishing a beta package N.M.Ob**XXX** (**XXX** is an increaing number) on [PyPI](https://pypi.org)
- tagging on a `beta/N.M.O` branch will publish an official package on [PyPI](https://pypi.org) for N.M.O 

See [here](https://pypi.org/project/setuptools-github/#history) for what the life cycle implementation looks like.

### Index

1. [Setup the project](#quickstart)
    - [install the package](#install)
    - [setup the __init__.py file](#initfile)
    - [fix the setup.py file](#setuppy)
2. [Setup the workflow files](#worflows)
    - [add the files](#workflows-add-files)
    - [setup the secrets](#workflows-setup-secrets)
3. [Working with branches](#branches)
    - [commit on the master branch](#master-branch)
    - [commit on a beta/N.M.O branch](#beta-branch)
    - [releasing on tags](#release-tag)


### Setup the project <a name="quickstart"/>

The project should conform to this layout style:
```text
  project-name/
  ├── setup.py
  ├── pyproject.toml
  ├── .github
  │   └── workflows           <- workflow files for
  │       ├── beta.yml             * beta/N.M.O branches
  │       ├── master.yml           * master branch
  │       └── tags.yml             * release/N.M.O tags
  ├── src
  │   └── project_name        <- project name
  │       └── __init__.py     <- version_file
  └── tests                   <- tests (pytest)
      ├── conftest.py
      └── requirements.txt    <- requirement file for tests
```

> **NOTE** for a pyproject.toml / hatch enabled version of this, please use
> [hatch-ci plugin](https://pypi.org/project/hatch-ci)


#### install the package <a name="install"/>
```bash
pip install setuptools-github
 or
conda install -c conda-forge setuptools-github
```

#### setup up the initial version_file <a name="initfile"/>
Create a new version_file `src/project_name/__init__.py` file to store the package information:
```
__version__ = "N.M.O"  # replace N, M and O with numerical values (eg. 0.0.0)
__hash__ = ""  # leave this empty
```

#### Fix the setup.py file <a name="setuppy"/>
Include in the `setup.py` file:
```
from setuptools_github import tools

setup(
  name="project-name",
  version=tools.process(version_file, os.getenv("GITHUB_DUMP"))["version"],
  ...
```
> **NOTE**: there's an annotated `tools.process` example in [setup.py](https://raw.githubusercontent.com/cav71/setuptools-github/master/setup.py)
> with support for keyword substitution on text files.

### Setup the workflow files <a name="worflows"/>
These are the steps to automate the build process on github.

#### add workflow files <a name="workflows-add-files"/>
Add these workflows file to your project:

- [github/workflows/master.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/master.yml)
- [github/workflows/beta.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/beta.yml)
- [github/workflows/tags.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/tags.yml)

This will trigger a build on a master branch XXX, a build on any 

> **NOTE**: Most likely you might need to change:
> - the `tests/requirements.txt` file
> - the envs variables at the beging of `master.yml` and `beta.yml`

#### Setup github secrets <a name="workflows-setup-secrets"/>
In order to publish to codecov the coveragen info and to PyPI the wheels,
you need to set the github secrets under:

https://github.com/<span style="color: red">username</span>/<span style="color: green">project-name</span>/settings/secrets/actions

These are the needed secrets for the PyPI index and codecov services:
- TWINE_PASSWORD
- TWINE_USERNAME
- CODECOV_TOKEN

---
THAT IS ALL! Now when commit to the master branch, this will trigger the 
github action to run tests and quality checks on the code 
---

### Working with branches  <a name="#branches"/>

#### commit on the master branch <a name="#master-branch"/>

Every time there's a commit on the **master** branch, this will trigger
the workflow under ./github/workflows/master.yml:
- Runs mypy on src/
- Runs ruff on src/
- Run all tests under tests/

On completion static and dynamic tests are supported.

#### commit on a beta/N.M.O branch <a name="#beta-branch"/>

In order to prepare for a release a new **beta/N.M.O** branch should be created:
```python

python -m setuptools_github.script make-beta src/project_name/__init__.py 
or
setuptools-github make-beta src/project_name/__init__.py
```

Every commit on **beta/N.M.O** branch if [Secrets](#add-secrets) have been set
properly:
- Runs mypy on src/
- Runs ruff on src/
- Run all tests under tests/
- Run coverage on tests/
- Send the coverage result into [coverage](https://coverage.io)
- Create a new wheel package under dist/
- (on success) Send the new wheels **package-N.M.O.bX** to [PyPI](https://pypi.org)

> NOTE: the name **project-N.M.O.bX** contains the X: this is an
> incrementing counter set during build.
> This means **project-N.M.O.bX** < **project-N.M.O** allowing 
> the correct package ordering.

#### releasing on tags
To release an official package for **project-N.M.O** from
the **beta/N.M.O** branch:
```python

python -m setuptools_github.script micro src/project_name/__init__.py
or
setuptools-github make-beta micro src/project_name/__init__.py
```
This will tag the HEAD on **beta/N.M.O** branch 
with the **release/N.M.O** tag and increment the **version_file** with the
next version N.M.O+1 (using micro).

Once done, you'll need to push it the tag.
```bash
git push release/N.M.O
```
This will:
- trigger a CI build that will create the project-name-N.M.O
- Create a new wheel package under dist/
- (on success) Send the new wheels **project-N.M.O** to [PyPI](https://pypi.org)
