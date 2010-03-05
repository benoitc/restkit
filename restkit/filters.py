# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
filters - Http filters

Http filters are object used before sending the request to the server
and after. The `HttpClient` instance is passed as argument.

An object with a method `on_request` is called just before the request. 
An object with a method `on_response` is called after fetching response headers.

ex::

    class MyFilter(object):
        
        def on_request(self, http_client):
            "do something with/to http_client instance"

        def on_response(self, http_client):
            "do something on http_client and get response infos"
            
            
"""

import base64
import os
import urlparse


from restkit.errors import InvalidUrl
from restkit.parser import Parser
from restkit import sock
from restkit import util
from restkit import __version__

class BasicAuth(object):
    """ Simple filter to manage basic authentification"""
    
    def __init__(self, username, password):
        self.credentials = (username, password)
    
    def on_request(self, req):
        encode = base64.encodestring("%s:%s" % self.credentials)[:-1]
        req.headers.append(('Authorization', 'Basic %s' %  encode))
        
class ProxyError(Exception):
    pass
            
class SimpleProxy(object):
    """ Simple proxy filter. 
    This filter find proxy from environment and if it exists it
    connect to the proxy and modify connection headers.
    """
    
    def _host_port(self, proxy_uri):
        proxy_host = proxy_uri.netloc
        i = proxy_host.rfind(':')
        j = proxy_host.rfind(']')         
        if i > j:
            try:
                proxy_port = int(proxy_host[i+1:])
            except ValueError:
                raise InvalidUrl("nonnumeric port: '%s'" % proxy_host[i+1:])
            proxy_host = proxy_host[:i]
        else:
            proxy_port = 80

        if proxy_host and proxy_host[0] == '[' and proxy_host[-1] == ']':
            proxy_host = proxy_host[1:-1]
            
        return proxy_host, proxy_port
    
    def on_request(self, req):
        proxy_auth = _get_proxy_auth()
        if req.uri.scheme == "https":
            proxy = os.environ.get('https_proxy')
            if proxy:
                if proxy_auth:
                    proxy_auth = 'Proxy-authorization: %s' % proxy_auth
                proxy_connect = 'CONNECT %s HTTP/1.0\r\n' % (req.uri.netloc)
                user_agent = "User-Agent: restkit/%s\r\n" % __version__
                proxy_pieces = '%s%s%s\r\n' % (proxy_connect, proxy_auth, 
                                        user_agent)
                proxy_uri = urlparse.urlparse(proxy)
                proxy_host, proxy_port = self._host_port(proxy_uri)
                # Connect to the proxy server, 
                # very simple recv and error checking
                
                p_sock = sock.connect((proxy_host, int(proxy_port))   )          
                sock.send(p_sock, proxy_pieces)
            
                # wait header
                p = Parser.parse_response()
                headers = []
                buf = ""
                buf = sock.recv(p_sock, util.CHUNK_SIZE)
                i = self.parser.filter_headers(headers, buf)
                if i == -1 and buf:
                    while True:
                        data = sock.recv(p_sock, util.CHUNK_SIZE)
                        if not data: break
                        buf += data
                        i = self.parser.filter_headers(headers, buf)
                        if i != -1: break
                        
                if p.status_int != 200:
                    raise ProxyError('Error status=%s' % p.status)
                    
                sock._ssl_wrap_socket(p_sock, None, None)
                
                # update socket
                req.socket = p_sock
                req.host = proxy_host
        else:
            proxy = os.environ.get('http_proxy')
            if proxy:
                proxy_uri = urlparse.urlparse(proxy)
                proxy_host, proxy_port = self._host_port(proxy_uri)
                if proxy_auth:
                    headers['Proxy-Authorization'] = proxy_auth.strip()
                    req.headers.append(('Proxy-Authorization', 
                             proxy_auth.strip()))
                req.host = proxy_host
                req.port = proxy_port
            
     
def _get_proxy_auth():
    proxy_username = os.environ.get('proxy-username')
    if not proxy_username:
        proxy_username = os.environ.get('proxy_username')
    proxy_password = os.environ.get('proxy-password')
    if not proxy_password:
        proxy_password = os.environ.get('proxy_password')
    if proxy_username:
        user_auth = base64.encodestring('%s:%s' % (proxy_username,
                                    proxy_password))
        return 'Basic %s\r\n' % (user_auth.strip())
    else:
        return ''
   