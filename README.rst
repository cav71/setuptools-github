=================
setuptools-github
=================

.. image:: https://img.shields.io/pypi/v/click-plus.svg
   :target: https://pypi.org/project/click-plus
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/click-plus.svg
   :target: https://pypi.org/project/click-plus
   :alt: Python versions

.. image:: https://github.com/cav71/click-plus/actions/workflows/master.yml/badge.svg
   :target: https://github.com/cav71/click-plus/actions
   :alt: Build

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Black

.. image:: https://codecov.io/gh/cav71/setuptools-github/branch/master/graph/badge.svg?token=SIUMZ7MT5T
   :target: https://codecov.io/gh/cav71/setuptools-github
   :alt: Coverage


This package manages the __version__ and __hash__ variables in a __init__.py file in the github actions-driven builds.

For each build in a specially named branch (eg. /beta/N.M.O) a wheel package will created with a __version__
set to N.M.Ob<build-number> to respect the order in `pep440` and a __hash__ set to the git hash.

A script **setuptools-github-start-release** will help to start a beta release branch.

Setup
-----

The starting point is the master branch.

First add into the setup.py::

   from setuptools_github import tools
   initfile = pathlib.Path(__file__).parent / "your_package/__init__.py"
   version = tools.update_version(initfile, os.getenv("GITHUB_DUMP"))
   
   setup(
        name="a-name",
        version=version,
        ...

Then insert into your_package/__init__.py::

    __version__ = "0.0.0"
    __hash__ = ""
    

The setuptools_github supports a simple but reliable way to maintain 
beta and release branches of a project.

The main model is rather simple, all the code gets developed on the **master** branch.

A branch (named **beta/N.M.O**) maintains all the beta releases for a particular release: each
one will have a version N.M.Ob<build-no>.
Finally tagging the code as **release/N.M.O**, will formalize the "release" for N.M.O.


Features
--------
Usage in setup.py::

   from setuptools_github import tools
   initfile = pathlib.Path(__file__).parent / "your_package/__init__.py"
   version = tools.update_version(initfile, os.getenv("GITHUB_DUMP"))
   
   setup(
        name="a-name",
        version=version,
        ...


Requirements
------------

* ``Python`` >= 3.7.
* ``setuptools``


Installation
------------

You can install ``setuptools-github`` via `pip`_ from `PyPI`_::

    $ pip install setuptools-github

Or conda::

    $ conda install -c conda-forge setuptools-github


.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
.. _`pep440`: https://peps.python.org/pep-0440
