# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
filters - Simple proxy 

"""

import base64
import os
import urlparse
import socket

from restkit import util

from restkit import __version__
        
class ProxyError(Exception):
    pass
            
class SimpleProxy(object):
    """ Simple proxy filter. 
    This filter find proxy from environment and if it exists it
    connect to the proxy and modify connection headers.
    """
    
    def on_connect(self, conn):
        proxy_auth = _get_proxy_auth()
        if conn.uri.is_ssl == "https":
            proxy = os.environ.get('https_proxy')
            if proxy:
                if proxy_auth:
                    proxy_auth = 'Proxy-authorization: %s' % proxy_auth
                proxy_connect = 'CONNECT %s:%s HTTP/1.0\r\n' % conn.addr
                user_agent = "User-Agent: restkit/%s\r\n" % __version__
                proxy_pieces = '%s%s%s\r\n' % (proxy_connect, proxy_auth, 
                                        user_agent)
                proxy_uri = urlparse.urlparse(proxy)
                proxy_host, proxy_port = util.parse_netloc(proxy_uri)
                
                route = ((proxy_host, proxy_port), True, None, {})
                pool = conn.get_pool(route)

                try:
                    p_sock = pool.request()
                except socket.error, e:
                    raise ProxyError(str(e))

                conn.sock = p_sock
                conn.addr = (proxy_host, proxy_port)
                conn.is_ssl = True

        else:
            proxy = os.environ.get('http_proxy')
            if proxy:
                proxy_uri = urlparse.urlparse(proxy)
                proxy_host, proxy_port = self._host_port(proxy_uri)
                if proxy_auth:
                    proxy.headers.append(('Proxy-Authorization', 
                             proxy_auth.strip()))
                proxy.addr = (proxy_host, proxy_port)       
            
     
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
