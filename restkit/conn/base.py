# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import threading

class Pool(object):
    """ Connection pull for a given route """

    def __init__(self, conn_manageer, route, timeout=300, 
            nb_connections=10):
        """ constructor for the pool

        :attr conn_manager: instance of ConnectionManager
        :attr route: tupple (address, is_ssl, filters, ssl_args)
        where address is a tuple of (host, port) and ssl_args a dict
        containing ssl arguments
        :attr timeout: integer, default timeout
        :attr nb_connections: integeger, number of connections in the
        pool
        """

    def requet(self):
        """ return a free connection """
        raise NotImplementedError

    def release(self, conn, duration=300):
        """ release a connection in the pool, and make it available for
        duration. """
        raise NotImplementedError

    def clean_iddle_duration(self):
        """ close any connections that haven been used in fixed duration
        """
        raise NotImplementedError

    def shutdown(self):
        """ close all connections in the pool """
        raise NotImplementedError

class ConnectionManager(object):
    """ maintain all connections pools. By default a pool have 10
    connections """

    POOL_CLASS = None

    def __init__(self, timeout=300, nb_connections=10):
        """ constructor for the manager

        :attr timeout: integer, default timeout
        :attr nb_connections: integeger, number of connections in the
        pool
        """
        self.timeout = timeout
        self.nb_connections = nb_connections
        self._connections = {}
        self._lock = self.init_lock()

    def init_lock(self):
        return threading.Lock()

    def get_key(self, route):
        key = (route[0], route[1])
        return key

    def get_pool(self, route):
        """ get a pool for given route

        where address is a tuple of (host, port) and ssl_args a dict
        containing ssl arguments
        """
        self._lock.acquire()
        try:
            key = self.get_key(route) 
            if key not in self._connections:
                pool = self.POOL_CLASS(self, route, timeout=self.timeout, 
                        nb_connections=self.nb_connections)
                self._connections[key] = pool
            else:
                pool = self._connections[key]
            return pool
        finally:
            self._lock.release() 
