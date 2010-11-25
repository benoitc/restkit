# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from restkit.conn.threaded import TConnectionManager

DEFAULT_MANAGER_CLASS = TConnectionManager

def set_default_manager_class(klass):
    global DEFAULT_MANAGER_CLASS
    DEFAULT_MANAGER_CLASS = klass

_default_manager = None
def get_default_manager():
    global _default_manager
    if not _default_manager:
        _default_manager = DEFAULT_MANAGER_CLASS()
    return _default_manager 

def reset_default_manager():
    global _default_manager
    _default_manager = DEFAULT_MANAGER_CLASS()

