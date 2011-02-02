# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
gevent connection manager. Instead of signaling we spawn the monitor
loop.
"""

import gevent
from gevent.coros import Semaphore
from gevent.event import Event

from .base import Manager

class GeventManager(Manager):

    def __init__(self, *kwargs):
        super(GeventManager, self).__init__(*kwargs)
        self._timeout_ev = Event()

    def get_lock(self):
        return Semaphore(1)

    def murder_connections(self):
        self._timeout_ev.clear()
        if self._timeout_ev.wait(self.timeout):
            super(GeventManager, self).murder_connections()
            gevent.spawn(self.murder_connections)

    def start(self):
        gevent.spawn(self.murder_connections)
