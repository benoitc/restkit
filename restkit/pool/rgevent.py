# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import gevent
from gevent import queue

from restkit.pool.monitored import MonitoredHost, MonitoredPool

class GeventHost(MonitoredHost):
    
    def init_pool(self):
        self.pool = queue.Queue()

    def do_get(self):
        return self.pool.get()
        
    def do_put(self, conn):
        self.pool.put(conn)
        
    def waiting(self):
        return max(0, len(self.pool.getters) - len(self.pool.putters))
        

class GeventPool(MonitoredPool):
    HOST_CLASS = GeventHost

    def start(self):
        self.loop = gevent.spawn(self.monitor_loop)
    
    def monitor_loop(self):
        while self.alive:
            gevent.sleep(0.1)
            for host in self._hosts.values():
                host.murder_connections()
        
