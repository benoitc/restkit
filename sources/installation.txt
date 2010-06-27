.. _installation:

Installation
============

Requirements
------------

- **Python 2.5 or newer** (Python 3.x will be supported soon)
- setuptools >= 0.6c6
- nosetests (for the test suite only)

Installing with easy_install
----------------------------

If you don't already have ``easy_install`` available you'll want to download and run the ``ez_setup.py`` script::

  $ curl -O http://peak.telecommunity.com/dist/ez_setup.py
  $ sudo python ez_setup.py -U setuptools

To install or upgrade to the latest released version of Restkit::

  $ sudo easy_install -U restkit

Installing from source
----------------------

You can install Restkit from source as simply as you would install any other Python package. Restkit uses setuptools which will automatically fetch all dependencies (including setuptools itself).

Get a Copy
++++++++++

You can download a tarball of the latest sources from `GitHub Downloads`_ or fetch them with git_::

    $ git clone git://github.com/benoitc/restkit.git

.. _`GitHub Downloads`: http://github.com/benoitc/restkit/downloads
.. _git: http://git-scm.com/

Installation
++++++++++++++++

::

  $ python setup.py install

If you've cloned the git repository, its highly recommended that you use the ``develop`` command which will allow you to use Restkit from the source directory. This will allow you to keep up to date with development on GitHub as well as make changes to the source::

  $ python setup.py develop
