#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys

setup(
    name = 'restclient',
    version = '0.1',
    description = 'Python REST client',
    long_description = \
"""A simple REST client for Python, inspired by the microframework (Camping, Sinatra…) style of specifying actions: get, put, post, delete.""",
    author = 'Benoit Chesneau',
    author_email = 'benoitc@e-engura.com',
    license = 'BSD',
    url = 'http://dev.e-engura.com/hg/python-restclient',
    zip_safe = True,

    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages = ['restclient'],
    test_suite = 'restclient.tests.suite',

    setup_requires = ['httplib2']

)

