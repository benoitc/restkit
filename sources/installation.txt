.. _installation:

Installation
============

Requirements
------------

- **Python 2.5 or newer** (Python 3.x will be supported soon)
- setuptools >= 0.6c6
- nosetests (for the test suite only)

Installation
------------

To install restkit using pip you must make sure you have a
recent version of distribute installed::

    $ curl -O http://python-distribute.org/distribute_setup.py
    $ sudo python distribute_setup.py
    $ easy_install pip

To install or upgrade to the latest released version of restkit::

    $ pip install http-parser
    $ pip install restkit


Note: if you get an error on MacOSX try to install with the following
arguments::

    $ env ARCHFLAGS="-arch i386 -arch x86_64" pip install http-parser
    
Installation from source
------------------------

You can install Restkit from source as simply as you would install any
other Python package. Restkit uses setuptools which will automatically
fetch all dependencies (including setuptools itself).

Get a Copy
++++++++++

You can download a tarball of the latest sources from `GitHub Downloads`_ or fetch them with git_::

    $ git clone git://github.com/benoitc/restkit.git

.. _`GitHub Downloads`: http://github.com/benoitc/restkit/downloads
.. _git: http://git-scm.com/

Installation
++++++++++++

::

  $ python setup.py install


Note: If you don't use setuptools or distribute, make sure http-parser
is installed first.
