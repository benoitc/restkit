# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import eventlet
from eventlet import queue

from restkit.pool.monitored import MonitoredHost, MonitoredPool

class EventletHost(MonitoredHost):
    
    def init_pool(self):
        self.pool = queue.LightQueue(0)

    def do_get(self):
        return self.pool.get()
        
    def do_put(self, conn):
        self.pool.put(conn)

    def monitor(self, conn):
        super(EventletHost, self).monitor(conn)
        eventlet.spawn_after(self.timeout, self.expire, conn.fileno())
        
    def waiting(self):
        return max(0, self.pool.getting() - self.pool.putting())   
        

class EventletPool(MonitoredPool):
    HOST_CLASS = EventletHost
