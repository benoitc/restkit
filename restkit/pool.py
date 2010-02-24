# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
Threadsafe Pool class 
"""

import collections
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
    

class ConnectionPool(PoolInterface):
    def __init__(self, max_connections=4):
        """ Initialize ConnectionPool
        :attr max_connections: int, the number of maximum connectioons 
        per _host_port
        """
        self.max_connections = max_connections
        self.hosts = {}
        
    def get(self, address):
        connections = self.hosts.get(address)
        if connections:
            socket = connections.popleft()
            self.hosts[address] = connections
            return socket
        return None
        
    def put(self, address, socket):
        connections = self.hosts.get(address)
        if not connections: 
            connections = collections.deque()
        
        # do we have already enough connections opened ?
        if len(connections) > self.max_connections:
            sock.close(socket)
            return
            
        connections.append(socket)
        self.hosts[address] = connections
        
    def clear(self, address):
        connections = self.hosts.get(address)
        while True:
            if not connections: break
            socket = connections.popleft()
            sock.close(socket)
            socket.close()