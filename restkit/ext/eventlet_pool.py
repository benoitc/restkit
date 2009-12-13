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

import os
import time
import urlparse

from eventlet.green import socket
from eventlet.green import httplib as ehttplib
from eventlet.pools import Pool
from eventlet.util import wrap_socket_with_coroutine_socket

import restkit
from restkit import errors
from restkit.pool import get_proxy_auth, PoolInterface

url_parser = urlparse.urlparse


wrap_socket_with_coroutine_socket()

eventlet_httplib = False
def wrap_eventlet_ehttplib():
    if eventlet_httplib: return
    import httplib
    ehttplib.BadStatusLine = httplib.BadStatusLine
    
wrap_eventlet_ehttplib()

class ConnectionPool(Pool, PoolInterface):
    def __init__(self, uri, use_proxy=False, key_file=None,
            cert_file=None, min_size=0, max_size=4, **kwargs):
        Pool.__init__(self, min_size, max_size)
        self.uri = uri
        self.use_proxy = use_proxy
        self.key_file = key_file
        self.cert_file = cert_file
        

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
            fake_sock = ehttplib.FakeSocket(p_sock, ssl)
            # Initalize ehttplib and replace with the proxy socket.
            connection = ehttplib.HTTPConnection(proxy_uri.host)
            connection.sock=fake_sock
            return connection
        else:
            proxy_uri = url_parser(proxy)
            if not proxy_uri.port:
                proxy_uri.port = '80'
            return ehttplib.HTTPConnection(proxy_uri.hostname, proxy_uri.port)
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
        if hasattr(ehttplib.HTTPConnection, 'timeout'):
            kwargs['timeout'] = self.timeout

        if self.uri.port:
            kwargs['port'] = self.uri.port

        if self.uri.scheme == "https":
            kwargs.update(dict(key_file=self.key_file, cert_file=self.cert_file))
            connection = ehttplib.HTTPSConnection(self.uri.hostname, **kwargs)
        else:
            connection = ehttplib.HTTPConnection(self.uri.hostname, **kwargs)

        setattr(connection, "started", time.time())
        return connection
    
    def create(self):
        return self.make_connection()
                
    def clear(self):
        self.free()