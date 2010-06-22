# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from gevent import spawn_later
from gevent import queue

from restkit.pool.monitored import MonitoredHost, MonitoredPool

class GeventHost(MonitoredHost):
    
    def init_pool(self):
        self.pool = queue.Queue(0)

    def do_get(self):
        return self.pool.get()
        
    def do_put(self, conn):
        self.pool.put(conn)

    def monitor(self, conn):
        super(GeventHost, self).monitor(conn)
        spawn_later(self.timeout, self.expire, conn.fileno())
        
    def waiting(self):
        return max(0, len(self.pool.getters) - len(self.pool.putters))
        

class GeventPool(MonitoredPool):
    HOST_CLASS = GeventHost
