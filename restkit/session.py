# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

from socketpool import ConnectionPool
from restkit.conn import Connection
_default_session = None

def get_session(backend_name, **options):
    global _default_session

    if not _default_session:
        _default_session = ConnectionPool(factory=Connection,
                backend=backend_name, **options)
    return _default_session
