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


Github Actions define a GITHUB_DUMP environmental variable during build: this package parses it and
it uses to create a "version" value from it depending on the branch name::

    For a package foobar on a beta/0.0.1 branch
        where __init__.py file contains __version__ = "0.0.1"

    setuptools_github.tools.update_version(initfile, os.getenv("GITHUB_DUMP"))
       returns -> 0.0.1.b<N> (N is the ever increasing build number)

**Version** can be used in the setup.py script to generate packages as foobar-0.0.0.b<N> that are semantically ordered.


Introduction
------------

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
