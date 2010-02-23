#!/usr/bin/env python
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import sys

if not hasattr(sys, 'version_info') or sys.version_info < (2, 5, 0, 'final'):
    raise SystemExit("Couchapp requires Python 2.5 or later.")

from setuptools import setup, find_packages


setup(
    name = 'restkit',
    version = '0.9.5',
    description = 'Python REST kit',
    long_description = \
"""An HTTP resource kit for Python""",
    author = 'Benoit Chesneau',
    author_email = 'benoitc@e-engura.org',
    license = 'BSD',
    url = 'http://bitbucket.org/benoitc/restkit/',
    zip_safe = True,

    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries',
    ],
    packages = find_packages(exclude=['tests']),
    entry_points = {
        'console_scripts': [
            'restcli = restkit.bin.rest_cli:main',
        ]
    },

    test_suite = 'nose.collector',

)

