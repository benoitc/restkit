#!/usr/bin/env python
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.
from __future__ import with_statement

try:
    from setuptools import setup
    use_setuptools = True
except ImportError:
    from distutils.core import setup
    use_setuptools = False

import glob
from imp import load_source
import os
import sys

if not hasattr(sys, 'version_info') or sys.version_info < (2, 5, 0, 'final'):
    raise SystemExit("Restkit requires Python 2.5 or later.")

extras = {}
try:
    import ssl
except ImportError:
    sys.stderr.write("Warning: On python 2.5x, https support requires "
                + " ssl module (http://pypi.python.org/pypi/ssl) "
                + "to be intalled.")


CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Software Development :: Libraries']

MODULES = [
    "restkit",
    "restkit.contrib",
    "restkit.manager"]

SCRIPTS = ['scripts/restcli']

def main():
    version = load_source("version", os.path.join("restkit",
        "version.py"))

    # read long description
    with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
        long_description = f.read()

    PACKAGES = {}
    for name in MODULES:
        PACKAGES[name] = name.replace(".", "/")

    DATA_FILES = [
        ('restkit', ["LICENSE", "MANIFEST.in", "NOTICE", "README.rst",
                        "THANKS", "TODO.txt"])
        ]

    options=dict(
            name = 'restkit',
            version = version.__version__,
            description = 'Python REST kit',
            long_description = long_description,
            author = 'Benoit Chesneau',
            author_email = 'benoitc@e-engura.org',
            license = 'BSD',
            url = 'http://benoitc.github.com/restkit',
            classifiers = CLASSIFIERS,
            packages = PACKAGES.keys(),
            package_dir = PACKAGES,
            data_files = DATA_FILES,
            scripts = SCRIPTS
        )

    if use_setuptools:
        options.update({
            'zip_safe': False,
            'entry_points': {
                'paste.app_factory': [
                        'proxy = restkit.contrib.wsgi_proxy:make_proxy',
                        'host_proxy = restkit.contrib.wsgi_proxy:make_host_proxy',
                        'couchdb_proxy = restkit.contrib.wsgi_proxy:make_couchdb_proxy',
                    ]},
            'install_requires': ['http-parser>=0.5.4']})


    # Python 3: run 2to3
    try:
        from distutils.command.build_py import build_py_2to3
        from distutils.command.build_scripts import build_scripts_2to3
    except ImportError:
        pass
    else:
        options['cmdclass'] = {
            'build_py': build_py_2to3,
            'build_scripts': build_scripts_2to3,
        }

    setup(**options)
    
if __name__ == "__main__":
    main()
