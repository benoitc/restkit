# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
Threadsafe Pool class 
"""

import collections
import logging
import threading

from restkit import sock

log = logging.getLogger(__name__)

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
        self._lock = threading.Lock()
    

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
            if host:
                
                socket = self._get_connection(host)
                log.debug("Got from pool [%s]" % str(address))
                self.hosts[address] = host
                return socket
            log.info("don't get from pool %s" % str(self.hosts))
            return None
        finally:
            self._lock.release()
        
    def put(self, address, socket):
        self._lock.acquire()
        try:
            host = self.hosts.get(address)
            if not host:
                host = _Host(address)
                self.hosts[address] = host
            self._add_connection(host, socket)
            log.info("put sock in pool (%s)" % str(len(host.pool)))    
            self.hosts[address] = host
        finally:
            self._lock.release()
            
    def _add_connection(self, host, socket):
        host._lock.acquire()
        try:
            if len(host.pool) > self.max_connections:
                sock.close(socket)
                return
            host.pool.append(socket)
        finally:
            host._lock.release()

    def _get_connection(self, host):
        host._lock.acquire()
        try:
            if len(host.pool) > 0:
                return host.pool.popleft()
            return None
        finally:
            host._lock.release()

    def clean(self, address):
        self._lock.acquire()
        try:
            host = self.hosts.get(address)
            if not host:
                return
            while True:
                socket = self._get_connection(host)
                if not socket:
                    break
                sock.close(socket)
            self.hosts[address] = host
        finally:
            self._lock.release()