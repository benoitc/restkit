# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import time

from restkit.conn.base import Pool, ConnectionManager
from restkit.conn import http_connection

from eventlet.green import socket
from eventlet.green import ssl
from eventlet import queue
from eventlet import semaphore

class EventletHttpConnection(http_connection.HttpConnection):

    def connect(self):
        self.filters.apply("on_connect", self)

        self.sock = socket.create_connection(self.addr,
                timeout=self.timeout)
        if self.is_ssl:
            self.sock = ssl.GreenSSLSocket(self.sock, **self.kwargs)
        
        


class EventletPool(Pool):

    def __init__(self, conn_manager, route, timeout=300, 
            nb_connections=10):
        self.conn_manager = conn_manager
        self.route = route
        self.nb_connections = nb_connections
        self.timeout = timeout
        self.connections = queue.PriorityQueue()
        self.iddle_connections = {}
        self.active_connections = {}

    def request(self):
        self.clean_iddle_connections()
        try:
            expires, conn = self.connections.get_nowait()
        except queue.Empty:
            conn = EventletHttpConnection(
                self.conn_manager,
                self.route[0], 
                self.route[1], 
                timeout=self.timeout,
                filters=self.route[2], 
                **self.route[3])
        return conn

    def release(self, conn, duration=300):
        if self.connections.qsize() >= self.nb_connections:
            conn.close()
            return
        expires = time.time() + duration
        self.connections.put_nowait((expires, conn))
        
    def clean_iddle_connections(self):
        while True:
            try:
                expires, conn = self.connections.get_nowait()
            except queue.Empty:
                break
            if time.time() > expires:
                conn.close()
            else:
                self.connections.put((expires, conn))
                break

    def shutdown(self):
        while True:
            try:
                expires, conn = self.connections.get_nowait()
                conn.close()
            except queue.Empty:
                break

    
class EventletConnectionManager(ConnectionManager):

    POOL_CLASS = EventletPool

    def init_lock(self):
        return semaphore.Semaphore(1)
