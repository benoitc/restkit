# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.



class BasePool(object):
    
    def __init__(self, keepalive=10, timeout=300):
        """ abstract class from which all connection 
        pool should inherit.
        """
        if type(timeout) != type(1):
            raise ValueError("Pool timeout isn't an integer")
        self.keepalive = keepalive
        self.timeout = timeout
        self.alive = True
        
    def get(self, netloc):
        """ method used to return a connection from the pool"""
        raise NotImplementedError
        
    def put(self, netloc, conn):
        """ Put an item back into the pool, when done """
        raise NotImplementedError
        
    def clear_host(self, netloc):
        """ method to clear all connections from host """
        raise NotImplementedError
        
    def clear(self):
        """ method used to release all connections """
        raise NotImplementedError
        
    def close(self):
        """ close the pool monitoring and clear all connections """
        self.alive = False
        self.clear()