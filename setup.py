#!/usr/bin/env python
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

from __future__ import with_statement
from setuptools import setup, find_packages

import glob
from imp import load_source
import os
import sys

if not hasattr(sys, 'version_info') or sys.version_info < (2, 6, 0, 'final'):
    raise SystemExit("Restkit requires Python 2.6 or later.")

extras = {}

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Software Development :: Libraries']


SCRIPTS = ['scripts/restcli']

def main():
    version = load_source("version", os.path.join("restkit",
        "version.py"))

    # read long description
    with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
        long_description = f.read()

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
            packages = find_packages(),
            data_files = DATA_FILES,
            scripts = SCRIPTS,
            zip_safe =  False,
            entry_points =  {
                'paste.app_factory': [
                    'proxy = restkit.contrib.wsgi_proxy:make_proxy',
                    'host_proxy = restkit.contrib.wsgi_proxy:make_host_proxy',
                    'couchdb_proxy = restkit.contrib.wsgi_proxy:make_couchdb_proxy',
                ]},
            install_requires = [
                'http-parser>=0.7.4',
                'socketpool']
        )


    setup(**options)

if __name__ == "__main__":
    main()
