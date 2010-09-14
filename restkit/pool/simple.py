# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

""" Thread-safe pool """
import collections
import time
try:
    import threading
except ImportError:
    import dummy_threading as threading

from restkit.pool.base import BasePool
from restkit.util import sock

class Host(object):
    
    def __init__(self, keepalive, timeout):
        self.keepalive = keepalive
        self.timeout  = timeout
        self.connections = collections.deque()
        
    def get(self):
        while len(self.connections):
            conn, expires = self.connections.popleft()
            if expires >= time.time():
                return conn
        return None
        
    def put(self, conn):
        if len(self.connections) >= self.keepalive:
            sock.close(conn)
            return
        expires = time.time() + self.timeout
        self.connections.append((conn, expires))
        
    def clear(self):
        while self.connections:
            conn, expires = self.connections.popleft()
            sock.close(conn)

class SimplePool(BasePool):
    
    def __init__(self, keepalive=10, timeout=300):
        super(SimplePool, self).__init__(keepalive=keepalive, 
                        timeout=timeout)
        self._hosts = {}
        self._lock = threading.Lock()
        
    def get(self, netloc):
        self._lock.acquire()
        try:
            if netloc not in self._hosts:
                return
            host = self._hosts[netloc]     
            conn = host.get()
            return conn
        finally:
            self._lock.release()
            
    def put(self, netloc, conn):
        self._lock.acquire()
        try:
            if netloc not in self._hosts:
                host = Host(self.keepalive, self.timeout)
                self._hosts[netloc] = host
            else:
                host = self._hosts[netloc] 
            host.put(conn)
        finally:
            self._lock.release()
            
    def clear_host(self, netloc):
        self._lock.acquire()
        try:
            if netloc not in self._hosts:
                return
            host = self._hosts[netloc]
            host.clear()
        finally:
            self._lock.release()
            
    def clear(self):
        self._lock.acquire()
        try:
            for netloc, host in self._hosts.items():
                host.clear()
                del self._hosts[netloc]
        finally:
            self._lock.release()
        
        

