# -*- coding: utf-8 -
#
# Copyright (c) 2008, 2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


"""
Threadsafe Pool class 

TODO:
- log errors
"""

import os
import time
import collections
import httplib
import socket
import urlparse

import restkit
from restkit import errors

has_timeout = hasattr(socket, '_GLOBAL_DEFAULT_TIMEOUT')
url_parser = urlparse.urlparse

def get_proxy_auth():
  import base64
  proxy_username = os.environ.get('proxy-username')
  if not proxy_username:
    proxy_username = os.environ.get('proxy_username')
  proxy_password = os.environ.get('proxy-password')
  if not proxy_password:
    proxy_password = os.environ.get('proxy_password')
  if proxy_username:
    user_auth = base64.b64encode('%s:%s' % (proxy_username,
                                            proxy_password))
    return 'Basic %s\r\n' % (user_auth.strip())
  else:
    return ''

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
    def __init__(self, uri, use_proxy=False, key_file=None, cert_file=None, 
            timeout=300, min_size=0, max_size=4):
        
        self.uri = uri
        self.use_proxy = use_proxy
        self.key_file = key_file
        self.cert_file = cert_file
        self.timeout = timeout
        self.min_size = min_size
        self.max_size = max_size
                    
        self.connections = collections.deque()
        for x in xrange(min_size):
            self.current_size += 1
            self.connections.append(self.make_connection())
            
    def _make_proxy_connection(self, proxy):
        if self.uri.scheme == 'https':
            proxy_auth = get_proxy_auth()
            if proxy_auth:
                proxy_auth = 'Proxy-authorization: %s' % proxy_auth
            port = self.uri.port
            if not port:
                port = 443
            proxy_connect = 'CONNECT %s:%s HTTP/1.0\r\n' % (self.uri.hostname, port)
            user_agent = 'User-Agent: %s\r\n' % restkit.USER_AGENT
            proxy_pieces = '%s%s%s\r\n' % (proxy_connect, proxy_auth, user_agent)
            proxy_uri = url_parser(proxy)
            if not proxy_uri.port:
                proxy_uri.port = '80'
            # Connect to the proxy server, very simple recv and error checking
            p_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            p_sock.connect((proxy_uri.host, int(proxy_uri.port)))
            p_sock.sendall(proxy_pieces)
            response = ''
            # Wait for the full response.
            while response.find("\r\n\r\n") == -1:
                response += p_sock.recv(8192)
            p_status = response.split()[1]
            if p_status != str(200):
                raise errors.ProxyError('Error status=%s' % str(p_status))
            # Trivial setup for ssl socket.
            ssl = socket.ssl(p_sock, None, None)
            fake_sock = httplib.FakeSocket(p_sock, ssl)
            # Initalize httplib and replace with the proxy socket.
            connection = httplib.HTTPConnection(proxy_uri.host)
            connection.sock=fake_sock
            return connection
        else:
            proxy_uri = url_parser(proxy)
            if not proxy_uri.port:
                proxy_uri.port = '80'
            return httplib.HTTPConnection(proxy_uri.hostname, proxy_uri.port)
        return None

    def make_connection(self):
        if self.use_proxy:
            proxy = ''
            if self.uri.scheme == 'https':
                proxy = os.environ.get('https_proxy')
            elif self.uri.scheme == 'http':
                proxy = os.environ.get('http_proxy')
                
            if proxy:
                return self._make_proxy_connection(proxy)
            
        kwargs = {}
        if hasattr(httplib.HTTPConnection, 'timeout'):
            kwargs['timeout'] = self.timeout
        
        if self.uri.port:
            kwargs['port'] = self.uri.port

        if self.uri.scheme == "https":
            kwargs.update(dict(key_file=self.key_file, cert_file=self.cert_file))
            connection = httplib.HTTPSConnection(self.uri.hostname, **kwargs)
        else:
            connection = httplib.HTTPConnection(self.uri.hostname, **kwargs)
            
        setattr(connection, "started", time.time())
        return connection
            
    def do_get(self):
        """
        Return an item from the pool, when one is available
        """ 
        if self.connections:
            connection = self.connections.popleft()
            return connection
        else:
            return self.make_connection()

    def get(self):
        while True:
            connection = self.do_get()
            since = time.time() - connection.started
            if since < self.timeout:
                if connection._HTTPConnection__response:
                    connection._HTTPConnection__response.read()
                return connection
            else:
                connection.close()
        
    def put(self, connection):
        if len(self.connections) >= self.max_size:
            connection.close()
            return
        if connection.sock is None:
            connection = self.make_connection()
        self.connections.append(connection)
            
    def clear(self):
        while self.connections:
            connection = self.connections.pop()
            connection.close()