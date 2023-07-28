# setuptools-github
[![PyPI version](https://img.shields.io/pypi/v/setuptools-github.svg?color=blue)](https://pypi.org/project/setuptools-github)
[![Python versions](https://img.shields.io/pypi/pyversions/setuptools-github.svg)](https://pypi.org/project/setuptools-github)
[![Build](https://github.com/cav71/setuptools-github/actions/workflows/master.yml/badge.svg)](https://github.com/cav71/setuptools-github/actions)
[![Coverage](https://codecov.io/gh/cav71/setuptools-github/branch/master/graph/badge.svg)](Coverage)

[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](Black)
[![License](https://img.shields.io/badge/License-BSD_2--Clause-blue.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![Types - Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://mypy-lang.org/)



## Quick start
setuptools-github helps to implement a simple project life cycle
aimed at delivering packages into [PyPI](https://pypi.org). Basically:
- beta packages are built from a /beta/N.M.O branch generating a **project-name-N.M.ObX** into PyPI
- tagging with /release/N.M.O a /beta/N.M.O branch commit will release **project-name-N.M.O**

This integrates well with the standard release logic in PyPI (see [example](https://pypi.org/project/setuptools-github/#history))

> **NOTE** for a pyproject.tom / hatch enabled version of this, please use
> [hatch-ci plugin](https://pypi.org/project/hatch-ci)

**Table of Contents**

- [Prerequisites](#prerequisites)
  - [Install](#install-setuptools-github)
  - [Add secrets](#add-secrets)
- [Project setup](#project-setup)


## Prerequisites

We make few assumption in the rest of this document:

- the project is hosted under https://www.github.com/<username>/<project-name>
- the github project is named <**project-name**>
- the main project branch is <**master**>
- you have coverage.io account https://app.codecov.io/gh/<username>/<project-name>

> **NOTE**: Please change **project-name**, **username** and **master** according to your project.

### Install setuptools-github

Install the package with:
```bash
pip install setuptools-github
 or
conda install -c conda-forge setuptools-github
```

### Add secrets

Github stores secrets for the <**project-name**> repository under:

https://github.com/<username>/<project-name>/settings/secrets/actions

These are the needed secrets for the PyPI index and codecov services:
- TWINE_PASSWORD
- TWINE_USERNAME
- CODECOV_TOKEN

## Project setup

### Layout
We assume this layout:
```python
  project-name/
  ├── .github
  │   └── workflows
  │       ├── beta.yml
  │       ├── master.yml
  │       └── tags.yml
  ├── pyproject.toml
  ├── src
  │   └── project_name        <- project name
  │       └── __init__.py     <- initfile
  └── tests                   <- tests (pytest)
      ├── conftest.py
      └── requirements.txt    <- requirement file for tests
```

- it is rooted under <**project-name**>/**src** directory
- the python package is **project_name**
- an **initfile** is stored under **project-name**/**src**/**project_name**/__init__.py
- **tests** are stored under **project-name**/**tests**
- a **requirements.txt* file for tests is under **project-name**/**tests**/requirements.txt

> **NOTE**: You need to change these values to match your project

### Setup the initfile

Create a new `src/project_name/__init__.py` file to store the package information:
```
__version__ = "N.M.O"  # replace N, M and O with numerical values (eg. 0.0.0)
__hash__ = ""  # leave this empty
```

Fix the setup.py file:
```
from setuptools_github import tools
initfile = pathlib.Path(__file__).parent / "project_name/__init__.py"
setup(
  name="project-name",
  version=tools.update_version(initfile, os.getenv("GITHUB_DUMP")),
  ...
```
Copy over the github workflow files:
- [github/workflows/master.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/master.yml)
- [github/workflows/beta.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/beta.yml)
- [github/workflows/tags.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/tags.yml)

Most likely you might need to change `tests/requirements.txt` file.

THAT IS ALL! Now when commit to the master branch, this will trigger the 
github action to run tests and quality checks on the code 
(see the Rationale section below).

### Working with the master branch

Every time there's a commit on the **master** branch, this will trigger
the workflow under ./github/workflows/master.yml:
- Runs mypy on src/
- Runs ruff on src/
- Run all tests under tests/

On completion static and dynamic tests are supported.

### Setup the beta/N.M.O branch

In order to prepare for a release a new **beta/N.M.O** branch should be created:
```python

python -m setuptools_github.script make-beta src/project_name/__init__.py 
or
setuptools-github make-beta src/project_name/__init__.py
```

Every commit on **beta/N.M.O** branch ASSUMING [Secrets](#add-secrets) have been set
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

### Release the project N.M.O
To release an official package for **project-N.M.O** from
the **beta/N.M.O** branch:
```python

python -m setuptools_github.script micro src/project_name/__init__.py
or
setuptools-github make-beta micro src/project_name/__init__.py
```
This will tag the HEAD on **beta/N.M.O** branch 
with the **release/N.M.O** tag and increment the **initfile** with the
next version N.M.O+1 (using micro).

Once done, you'll need to push it the tag.
```bash
git push release/N.M.O
```
This will:
- trigger a CI build that will create the project-name-N.M.O
- Create a new wheel package under dist/
- (on success) Send the new wheels **project-N.M.O** to [PyPI](https://pypi.org)
