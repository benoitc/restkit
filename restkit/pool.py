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
Threadsafe Pool class based on eventlet.pools.Pool but using Queue.Queue

TODO:
- add our own way to share socket across connections. We shouldn't need to rely
  on eventlet for that
- log errors
"""



import collections
import httplib
import Queue
import threading

from restkit import errors

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

def make_proxy_connection(uri):
    headers = headers or {}
    proxy = None
    if uri.scheme == 'https':
        proxy = os.environ.get('https_proxy')
    elif uri.scheme == 'http':
        proxy = os.environ.get('http_proxy')

    if not proxy:
        return make_connection(uri, use_proxy=False)
  
    if uri.scheme == 'https':
        proxy_auth = get_proxy_auth()
        if proxy_auth:
            proxy_auth = 'Proxy-authorization: %s' % proxy_auth
        port = uri.port
        if not port:
            port = 443
        proxy_connect = 'CONNECT %s:%s HTTP/1.0\r\n' % (uri.hostname, port)
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
            raise ProxyError('Error status=%s' % str(p_status))
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
    
def make_connection(uri, use_proxy=True):
    if use_proxy:
        return make_proxy_connection(uri)
    
    if uri.scheme == 'https':
        if not uri.port:
            connection = httplib.HTTPSConnection(uri.hostname)
        else:
            connection = httplib.HTTPSConnection(uri.hostname, uri.port)
    else:
        if not uri.port:
            connection = httplib.HTTPConnection(uri.hostname)
        else:
            connection = httplib.HTTPConnection(uri.hostname, uri.port)
    return connection

class Pool(object):
    def __init__(self, min_size=0, max_size=4, order_as_stack=False):
        self.min_size = min_size
        self.max_size = max_size
        self.order_as_stack = order_as_stack
        self.current_size = 0
        self.channel = Queue.Queue(0)
        self.free_items = collections.deque()
        for x in xrange(min_size):
            self.current_size += 1
            self.free_items.append(self.create())
            
        self.lock = threading.Lock()
            
    def do_get(self):
        """
        Return an item from the pool, when one is available
        """ 
        self.lock.acquire()
        try:
            if self.free_items:
                return self.free_items.popleft()
            if self.current_size < self.max_size:
                created = self.create()
                self.current_size += 1
                return created
                
            try:
                return self.channel.get(False)
            except Queue.Empty:
                created = self.create()
                self.current_size += 1
                return created
                
        finally:
            self.lock.release()

    def get(self):
        connection =  self.do_get()
        return connection
        
    def put(self, item):
        """Put an item back into the pool, when done
        """
        self.lock.acquire()
        try:
            if self.current_size > self.max_size:
                self.current_size -= 1
                return
            
            if self.waiting():
                self.channel.put(item, False)
            else:
                if self.order_as_stack:
                    self.free_items.appendleft(item)
                else:
                    self.free_items.append(item)
        finally:
            self.lock.release()
            
    def resize(self, new_size):
        """Resize the pool
        """
        self.max_size = new_size
    
    def free(self):
        """Return the number of free items in the pool.
        """
        return len(self.free_items) + self.max_size - self.current_size
    
    def waiting(self):
        """Return the number of routines waiting for a pool item.
        """
        return self.channel.qsize() <= self.max_size
    
    def create(self):
        """Generate a new pool item
        """
        raise NotImplementedError("Implement in subclass")
                
class ConnectionPool(Pool):
    def __init__(self, uri, use_proxy=False, min_size=0, max_size=4):
        self.uri = uri
        self.use_proxy = use_proxy
        Pool.__init__(self, min_size, max_size)
    
    def create(self):
        return make_connection(self.uri, self.use_proxy)

    def put(self, connection):
        # close the connection if needed
        if connection.sock is not None:
            connection.close()

        if self.current_size > self.max_size:
            self.lock.acquire()
            self.current_size -= 1
            self.lock.release()
            return
        
        Pool.put(self, self.create())