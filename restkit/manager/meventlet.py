# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
eventlet connection manager. 
"""
from eventlet.semaphore import Semaphore

from .base import Manager

class EventletManager(Manager):

    def get_lock(self):
        return Semaphore(1)
