# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

from socketpool import ConnectionPool
from restkit.conn import Connection


_default_session = {}

def get_session(backend_name, **options):
    global _default_session

    if not _default_session:
        _default_session = {}
        pool = ConnectionPool(factory=Connection,
                backend=backend_name, **options)
        _default_session[backend_name] = pool
    else:
        if backend_name not in _default_session:
            pool = ConnectionPool(factory=Connection,
                backend=backend_name, **options)

            _default_session[backend_name] = pool
        else:
            pool = _default_session.get(backend_name)
    return pool

def set_session(backend_name, **options):

    global _default_session

    if not _default_session:
        _default_session = {}

    if backend_name in _default_session:
        pool = _default_session.get(backend_name)
    else:
        pool = ConnectionPool(factory=Connection,
                backend=backend_name, **options)
        _default_session[backend_name] = pool
    return pool
