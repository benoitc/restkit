# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import os
import time
import urlparse

import eventlet
from eventlet import queue
from eventlet.timeout import Timeout

from restkit.pool import PoolInterface
from restkit import sock

class EventletPool(PoolInterface):
    
    def __init__(self, max_connections=4, timeout=60):
        self.max_connections = max_connections
        self.timeout = 60
        self.hosts = {}
        self.sockets = {}
                
    def get(self, address):
        connections = self.hosts.get(address)
        if hasattr(connections, 'get'):
            try:
                socket = connections.get(False)
                self.hosts[address] = connections
                del self.sockets[socket.fileno()]
                return socket
            except queue.Empty:
                pass
        return None
                
    def monitor_socket(self, fn):
        with Timeout(self.timeout, False):
            if fn in self.sockets:
                socket = self.sockets[fn]
                sock.close(socket)
                del self.sockets[fn]
        
    def put(self, address, socket):
        connections = self.hosts.get(address)
        if not connections: 
            connections = queue.LightQueue(None)
        
        # do we have already enough connections opened ?
        if connections.qsize() > self.max_connections:
            sock.close(socket)
            return
            
        connections.put(socket, False)
        self.sockets[socket.fileno()] = socket
        eventlet.spawn(self.monitor_socket, socket.fileno())
        self.hosts[address] = connections
        
    def clear(self, address):
        connections = self.hosts.get(address)
        while True:
            try:
                socket = connections.get(False)
                sock.close(socket)
                socket.close()
            except queue.Empty:
                break
        