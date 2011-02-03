# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
gevent connection manager. 
"""
import signal

import gevent
from gevent.coros import RLock

from .base import Manager

class GeventConnectionReaper(gevent.Greenlet):

    running = False

    def __init__(self, manager, delay=150):
        self.manager = manager
        self.delay = delay
        gevent.Greenlet.__init__(self)  

    def _run(self):
        self.running = True
        while True:
            gevent.sleep(self.delay)
            self.manager.murder_connections()

    def ensure_started(self):
        if not self.running or self.ready():
            self.start()

class GeventManager(Manager):

    def get_lock(self):
        return RLock()
           
    def start(self):
        if self.with_signaling:
            signal.signal(signal.SIGALRM, self.murder_connections)
            signal.alarm(self.timeout)
        else:
            self._reaper = GeventConnectionReaper(self, delay=self.timeout)
            self._reaper.ensure_started()

