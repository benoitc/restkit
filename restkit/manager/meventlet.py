# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
eventlet connection manager. 
"""
import signal

import eventlet
from eventlet.semaphore import Semaphore

from restkit.manager.base import Manager

class EventletConnectionReaper(object):

    running = False

    def __init__(self, manager, delay=150):
        self.manager = manager
        self.delay = delay

    def start(self):
        self.running = True
        g = eventlet.spawn(self._exec) 
        g.link(self._exit)
    
    def _exit(self, g):
        try:
            g.wait()
        except:
            pass
        self.running = False
    
    def _exec(self):
        while True:
            eventlet.sleep(self.delay)
            self.manager.murder_connections()

    def ensure_started(self):
        if not self.running:
            self.start()

class EventletManager(Manager):

    def get_lock(self):
        return Semaphore(1)

    def start(self):
        if self.with_signaling:
            signal.signal(signal.SIGALRM, self.murder_connections)
            signal.alarm(self.timeout)
        else:
            self._reaper = EventletConnectionReaper(self, delay=self.timeout)
            self._reaper.ensure_started()
