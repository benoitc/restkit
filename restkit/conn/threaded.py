# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import time
import collections
import threading

from restkit.conn.base import Pool, ConnectionManager
from restkit.conn.http_connection import HttpConnection
from restkit.util import sock

class TPool(Pool):

    def __init__(self, conn_manager, route, timeout=300, 
            nb_connections=10):
        self.conn_manager = conn_manager
        self.route = route
        self.nb_connections = nb_connections
        self.timeout = timeout
        self.connections = collections.deque()
        self.active_connections = {}
        self._lock = threading.Lock()

    def request(self):
        self.clean_iddle_connections()
        
        try:
            conn, expires = self.connections.popleft()
        except IndexError:
            conn = HttpConnection(
                    self.conn_manager,
                    self.route[0], 
                    self.route[1], 
                    timeout=self.timeout,
                    filters=self.route[2], 
                    **self.route[3])
        self.active_connections[conn] = (conn, time.time())
        return conn

    def release(self, conn, duration=300):
        if conn not in self.active_connections or \
                len(self.connections) > self.nb_connections:
            conn.close()
            return
        expires = time.time() + duration
        self.connections.append((conn, expires))
        del self.active_connections[conn]

    def clean_iddle_connections(self):
        self._lock.acquire()
        try:
            for conn, duration in self.connections:
                if time.time() > duration:
                    self.connections.remove((conn, duration))
                else:
                    # no need to continue since we are ordered.
                    break
        finally:
            self._lock.release()
    
    def shutdown(self):
        while self.connections:
            conn, expires = self.connections.pop()
            sock.close(conn)

class TConnectionManager(ConnectionManager):
    
    POOL_CLASS = TPool
