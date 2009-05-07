#!/usr/bin/env python
# -*- coding: utf-8 -
#
# Copyright (c) 2008 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages

import sys

setup(
    name = 'py-restclient',
    version = '1.3.2',
    description = 'Python REST client',
    long_description = \
"""A simple REST client for Python, inspired by the microframework (Camping, Sinatra) style of specifying actions: get, put, post, delete.""",
    author = 'Benoit Chesneau',
    author_email = 'benoitc@e-engura.org',
    license = 'BSD',
    url = 'http://py-restclient.e-engura.org',
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
    packages = find_packages(),

    entry_points = {
        'console_scripts': [
            'restcli = restclient.bin.rest_cli:main',
        ]
    },

    install_requires = [
        'httplib2'
    ],

    test_suite = 'nose.collector',

)

