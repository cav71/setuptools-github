=================
setuptools-github
=================

This extends setuptools with method to create beta and releases for projects.

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


Features
--------
Usage in setup.py:
```python
initfile = pathlib.Path(__file__).parent / "your_package/__init__.py"
version = tools.update_version(initfile, os.getenv("GITHUB_DUMP"))
```


Requirements
------------

* ``Python`` >= 3.6.
* ``setuptools``

Installation
------------

You can install ``setuptools-github`` via `pip`_ from `PyPI`_::

    $ pip install setuptools-github


.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
