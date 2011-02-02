# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from .manager import Manager

_manager = None

def set_manager(manager_class=None):
    global _manager
    _manager = manager_class()

def set_default_manager():
    global _manager
    if _manager is None:
        _manager = Manager()

def get_manager():
    global _manager
    if _manager is None:
        set_default_manager()
    return _manager

set_default_manager()

