# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import socket

from restkit.pool.base import BasePool
from restkit.util import sock

class MonitoredHost(object):

    def __init__(self, keepalive, timeout):
        self.keepalive = keepalive
        self.timeout = timeout
        self.nb_connections = 0
        self.alive = dict()
        self.init_pool()

    def get(self):
        while self.nb_connections:
            self.nb_connections -= 1
            conn = self.do_get()
            try:
                _ = conn.fileno()
                return conn
            except socket.error:
                """ connection probably closed """
                continue
        return None
        
    def put(self, conn):
        if self.nb_connections < self.keepalive and not self.waiting():
            sock.close(conn)
            return
        self.nb_connections += 1
        self.do_put(conn)
        self.monitor(conn)
        
    def clear(self):
        while self.nb_connections:
            conn = self.get()
            sock.close(conn)
            
    def expire(self, fno):
        if fno in self.alive:
            conn = self.alive.pop(fno)
            sock.close(conn)

    def monitor(self, conn):
        self.alive[conn.fileno()] = conn
        
    def init_pool(self):
        raise NotImplementedError
        
    def do_get(self):
        raise NotImplementedError
        
    def do_put(self, conn):
        raise NotImplementedError
        
    def waiting(self):
        raise NotImplementedError
    

class MonitoredPool(BasePool):
    
    HOST_CLASS = None
    
    def __init__(self, *args, **kwargs):
        BasePool.__init__(self, *args, **kwargs)
        self._hosts = {}
        
    def get(self, netloc):
        if netloc not in self._hosts:
            return
        host = self._hosts[netloc]
        return host.get()
            
    def put(self, netloc, conn):
        if netloc in self._hosts:
            host = self._hosts[netloc]
        else:
            host = self.HOST_CLASS(self.keepalive, self.timeout)
            self._hosts[netloc] = host
        host.put(conn)

    def clear_host(self, netloc):
        if netloc not in self._hosts:
            return
        host = self._hosts[netloc]
        host.clear()
        del self._hosts[netloc]
        
    def clear(self):
        for netloc, host in self._hosts.items():
            host.clear()
            del self._hosts[netloc]
        
        
        
