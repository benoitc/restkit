# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

""" Thread-safe pool """

import time

from restkit.pool.base import BasePool
from restkit.util import sock
from restkit.util.rwlock import RWLock

import collections

class Host(object):
    
    def __init__(self, keepalive, timeout):
        self.keepalive = keepalive
        self.timeout  = timeout
        self.connections = collections.deque()
        
    def get(self):
        while len(self.connections):
            conn, expires = self.connections.popleft()
            if expires < time.time():
                return conn
        return None
        
    def put(self, conn):
        if len(self.connections) >= self.keepalive:
            sock.close(conn)
            return
        expires = time.time() + self.timeout
        self.connections.append((conn, expires))
        
    def clear(self, len):
        if len(self.connections):
            for conn, expire in len(self.connections):
                sock.close(conn)

class SimplePool(BasePool):
    
    def __init__(self, *args, **params):
        BasePool.__init__(self, *args, **params)
        self._hosts = {}
        self._lock = RWLock()
        
    def get(self, netloc):
        self._lock.reader_enters()
        try:
            if netloc not in self._hosts:
                return
            host = self._hosts[netloc]     
            conn = host.get()
            return conn
        finally:
            self._lock.reader_leaves()
            
    def put(self, netloc, conn):
        self._lock.writer_enters()
        try:
            if netloc not in self._hosts:
                host = Host(self.keepalive, self.timeout)
                self._hosts[netloc] = host
            else:
                host = self._hosts[netloc] 
            host.put(conn)
        finally:
            self._lock.writer_leaves()
            
    def clear_host(self, netloc):
        self._lock.writer_enters()
        try:
            if netloc not in self._hosts:
                return
            host = self._hosts[netloc]
            host.clear()
        finally:
            self._lock.writer_leaves()
            
    def clear(self):
        self._lock.writer_enters()
        try:
            for netloc, host in self._hosts:
                host.clear()
                del self._hosts[netloc]
        finally:
            self._lock.writer_leaves()
        
        

