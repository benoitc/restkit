# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import eventlet
from eventlet import queue
from eventlet.timeout import Timeout

from restkit.pool import PoolInterface
from restkit import sock

class EventletPool(PoolInterface):
    """
    Eventlet pool to manage connections. after a specific timeout the
    sockets are closes. Default timeout is 300s.
    
    To use restkit with eventlet::
    
        import eventlet
        eventlet.monkey_patch(all=False, socket=True, select=True)
        from restkit import request
        from restkit.ext.eventlet_pool import EventletPool
        pool = EventletPool()
        r = request('http://openbsd.org', pool_instance=pool)
    """
    
    def __init__(self, max_connections=4, timeout=300):
        """ Initialize EventletPool 
        
        :param max_connexions: int, number max of connections in the pool. 
        Default is 4
        :param timeout: int, number max of second a connection is kept alive. 
        Default is 300s.
        """
        self.max_connections = max_connections
        self.timeout = 60
        self.hosts = {}
        self.sockets = {}
                
    def get(self, address):
        """ Get connection for (Host, Port) address 
        :param address: tuple (Host, address)
        """
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
        """ function used to monitor the socket """
        with Timeout(self.timeout, False):
            if fn in self.sockets:
                socket = self.sockets[fn]
                sock.close(socket)
                del self.sockets[fn]
        
    def put(self, address, socket):
        """ release socket in the pool 
        
        :param address: tuple (Host, address)
        :param socket: a socket object 
        """
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
        """ close all sockets in the pool for this address 
        
        :param address: tuple (Host, address)
        """
        connections = self.hosts.get(address)
        while True:
            try:
                socket = connections.get(False)
                sock.close(socket)
                socket.close()
            except queue.Empty:
                break
        