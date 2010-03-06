# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
Threadsafe Pool class 
"""

import collections
import threading

from restkit import sock

class PoolInterface(object):
    """ abstract class from which all connection 
    pool should inherit.
    """

    def get(self):
        """ method used to return a connection from the pool"""
        raise NotImplementedError
        
    def put(self):
        """ Put an item back into the pool, when done """
        raise NotImplementedError
        
    def clear(self):
        """ method used to release all connections """
        raise NotImplementedError
        
        
class _Host(object):
    """ An host entry """
    
    def __init__(self, addr):
        object.__init__(self)
        self._addr = addr
        self.pool = collections.deque()    

class ConnectionPool(PoolInterface):
    def __init__(self, max_connections=4):
        """ Initialize ConnectionPool
        :attr max_connections: int, the number of maximum connectioons 
        per _host_port
        """
        self.max_connections = max_connections
        self.hosts = {}
        self._lock = threading.Lock()
        
        
    def get(self, address):
        self._lock.acquire()
        try:
            host = self.hosts.get(address)
            if not host:
                return None
                
            if host.pool:
                return host.pool.popleft()
                
            return None
        finally:
            self._lock.release()
        
    def put(self, address, socket):
        self._lock.acquire()
        try:
            host = self.hosts.get(address)
            if not host:
                host = _Host(address)
                
            if len(host.pool) > self.max_connections:
                sock.close(socket)
                return
            host.pool.append(socket) 
        finally:
            self._lock.release()

    def clean(self, address):
        self._lock.acquire()
        try:
            host = self.hosts.get(address)
            if not host: return
            while host.pool:
                socket = host.pool.popleft()
                sock.close(socket)
        finally:
            self._lock.release()