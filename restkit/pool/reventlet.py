# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import eventlet
from eventlet import queue

from restkit.pool.monitored import MonitoredHost, MonitoredPool

class EventletHost(MonitoredHost):
    
    def init_pool(self):
        self.pool = queue.LightQueue()

    def do_get(self):
        return self.pool.get()
        
    def do_put(self, conn):
        self.pool.put(conn)
        
    def waiting(self):
        return max(0, self.pool.getting() - self.pool.putting())   
        

class EventletPool(MonitoredPool):
    HOST_CLASS = EventletHost
    
    def start(self):
        self.loop = eventlet.spawn(self.monitor_loop)
    
    def monitor_loop(self):
        while self.alive:
            eventlet.sleep(0.1)
            for host in self._hosts.values():
                host.murder_connections()