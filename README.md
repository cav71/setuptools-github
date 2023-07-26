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
aimed at delivering packages into [PyPI](https://pypi.org).

**Table of Contents**
- [Prerequisites](#setup-prerequisites)
  - [Install](#setup-install)
  - [Add secrets](#setup-add-secrets)


## Prerequisites

In the following we assume these:

- the project is named **project-name**
- the main project branch is **master**
- the project is hosted under http://www.github.com\/**username**/**project-name**
- you have coverage.io account https://app.codecov.io\/gh/**username**/**project-name**

> **NOTE**: You need to change **project-name**, **username** and **master** to match your project.

### Install

Install the package with:
```bash
pip install setuptools-github
 or
conda install -c conda-forge setuptools-github
```

### Add secrets

Secrets are stored for the **package-name** repository under:

https:\//github.com/**username**/**project-name**/settings/secrets/actions)

These are needed:
- TWINE_PASSWORD
- TWINE_USERNAME
- CODECOV_TOKEN


### Setup the master branch
Create a new `src/package_name/__init__.py` file to store the package information:
```
__version__ = "N.M.O"  # replace N, M and O with numerical values (eg. 0.0.0)
__hash__ = ""  # leave this empty
```

Fix the setup.py file:
```
from setuptools_github import tools
initfile = pathlib.Path(__file__).parent / "package_name/__init__.py"
setup(
  name="package-name",
  version=tools.update_version(initfile, os.getenv("GITHUB_DUMP")),
  ...
```
Copy over the github workflow files:
- [github/workflows/master.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/master.yml)
- [github/workflows/beta.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/beta.yml)
- [github/workflows/tags.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/tags.yml)

Most likely you might need to change `tests/requirements.txt` file.

THAT IS ALL! Now when commiting to the master branch, this will trigger the 
github action to run tests and quality checks on the code 
(see the Rationale section below).

### Setup the beta/N.M.O branch

From the **master** branch, this will create a beta branch:
```python

python -m setuptools_github.script make-beta 
or
setuptools-github make-beta
```

Adds the secrets in https://github.com/<username>/<project-name>/settings/secrets/actions:
- TWINE_PASSWORD
- TWINE_USERNAME

Then for each commit into **beta/N.M.O** a package will be generated as
**package-N.M.O.bX** on [PyPI](https://pypi.org) (if all tests pass!).


### Release the package N.M.O

From the **beta/N.M.O** branch you can use:
```python

python -m setuptools_github.script micro 
or
setuptools-github make-beta micro
```
Once done, you'll need to push it.
```bash
git push release/N.M.I
```

This will:
- tag the HEAD on **beta/N.M.O** branch with the **release/N.M.O** tag
- trigger a CI build that will create the package-name-N.M.O
- will send to pypi




## Rationale
setuptools-github helps to implement a simple project life cycle
aimed at delivering packages into [PyPI](https://pypi.org): 
there are three important components, the **master** branch, 
the **beta** branch and the **release** tags.

`/master branch` this is the branch where all commit go 
(as well the PR from feature branches).
On each commit the CI will run code quality checks as:
  - running flake8
  - running mypy
  - running all pytest + coverage

(see [github/workflows/master.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/master.yml) for an example)

`/beta/N.M.O branch` branch is where code is merged to release the *beta*
packages to [PyPI](https://pypi.org).   
On each commit into this branch, the CI will:
  - run flake8
  - run mypy
  - run pytest + coverage (see *.github/workflows/master.yml*)
  - create wheel such as **package-N.M.O.bX**
  - (optional) publish the wheel to [PyPI](https://pypi.org)

(see [github/workflows/beta.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/beta.yml) for an example)

> NOTE: the **X** in the **package-name-N.M.O.bX** is a unique increasing 
> build number taken from GITHUB build environment.

`/release/N.M.O` is a release tag.
Once the code is stable enough on the **/beta/N.M.O** branch that is the
time to release a formal **package-N.M.O**.

So tagging on **/beta/N.M.O** with a **/release/N.M.O** tag will direct the
CI to:
  - create wheel such as **package-name-N.M.O**
  - (optional) publish the wheel to [PyPI](https://pypi.org)

(see [github/workflows/tags.yml](https://github.com/cav71/setuptools-github/blob/master/.github/workflows/tags.yml) for an example)

> WARNING: there won't be any check/test run on the tagged code, so it
> it important the tagging happen on **/beta/N.M.O** branch
