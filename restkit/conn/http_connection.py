# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import copy
import socket

from restkit.util import sock

class HttpConnection(object):

    def __init__(self, conn_manager,addr, is_ssl, timeout=300, 
            filters=None, **ssl_args):
        self.conn_manager = conn_manager
        self.filters = copy.copy(filters)
        self.addr = addr
        self.is_ssl = is_ssl 
        self.timeout = timeout
        self.ssl_args = ssl_args or {}
        self.headers = []
        self.params = {} 
        self.sock = None
        self.connect()

    def connect(self):
        self.filters.apply("on_connect", self)

        self.sock = sock.connect(self.addr, self.is_ssl, 
                self.timeout, **self.ssl_args)
        
    def socket(self):
        return self.sock

    def close(self):
        sock.close(self.sock)

        

