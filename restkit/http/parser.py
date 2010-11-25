# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import socket

from restkit.conn.http_connection import HttpConnection
from restkit.http.message import Request, Response
from restkit.http.unreader import ConnectionUnreader, SocketUnreader, \
IterUnreader

class Parser(object):
    def __init__(self, mesg_class, source, release_source=None, **kwargs):
        self.mesg_class = mesg_class
        if isinstance(source, HttpConnection):
             self.unreader = ConnectionUnreader(source, 
                     release_fun=release_source)
        elif isinstance(source, socket.socket):
            self.unreader = SocketUnreader(source, 
                    release_fun=release_source)
        else:
            self.unreader = IterUnreader(source, 
                    release_fun=release_source)
        self.mesg = None
        self.kwargs = kwargs

    def __iter__(self):
        return self
    
    def next(self):
        # Stop if HTTP dictates a stop.
        if self.mesg and self.mesg.should_close():
            raise StopIteration()
        
        # Discard any unread body of the previous message
        if self.mesg:
            data = self.mesg.body.read(8192)
            while data:
                data = self.mesg.body.read(8192)
        
        # Parse the next request
        self.mesg = self.mesg_class(self.unreader, **self.kwargs)
        if not self.mesg:
            raise StopIteration()
        return self.mesg

class RequestParser(Parser):
    def __init__(self, *args, **kwargs):
        super(RequestParser, self).__init__(Request, *args, **kwargs)
        
class ResponseParser(Parser):
    def __init__(self, *args, **kwargs):
        super(ResponseParser, self).__init__(Response, *args, **kwargs)
    
