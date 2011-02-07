# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import base64
import os
import re
import urlparse
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl
from urlparse import urlunparse

from . import __version__ 
from .errors import ProxyError
from .http import Request, Unreader
from .oauth2 import Consumer, Request, SignatureMethod_HMAC_SHA1,\
Token
from .sock import send
from .util import parse_netloc

class Filters(object):
    
    def __init__(self, filters=None):
        self.filters = filters or []
        
    def add(self, obj):
        if not hasattr(obj, "on_request") and not hasattr(obj, "on_response"):
            raise TypeError("%s is not a filter object." % obj.__class__.__name__)
            
        self.filters.append(obj)
        
    def remove(self, obj):
        for i, f in enumerate(self.filters):
            if obj == f: del self.filters[i]
            
    def apply(self, kind, *args):
        for f in self.filters:
            try:
                func = getattr(f, kind)
            except AttributeError:
                continue
            func(*args)

class BasicAuth(object):
    """ Simple filter to manage basic authentification"""
    
    def __init__(self, username, password):
        self.credentials = (username, password)
    
    def on_request(self, client):
        encode = base64.b64encode("%s:%s" % self.credentials)
        client.headers['Authorization'] = 'Basic %s' %  encode



class SimpleProxy(object):
    """ Simple proxy filter. 
    This filter find proxy from environment and if it exists it
    connect to the proxy and modify connection headers.
    """

    def on_connect(self, client, client_addr, ssl):
        proxy_settings = os.environ.get('%s_proxy' %
                client.parsed_url.scheme)

        if not proxy_settings: 
            return


        if proxy_settings:
            proxy_settings, proxy_auth =  _get_proxy_auth(proxy_setting)
            addr = parse_netloc(urlparse.urlparse(proxy_settings))

            if ssl:
                if proxy_auth:
                    proxy_auth = 'Proxy-authorization: %s' % proxy_auth
                proxy_connect = 'CONNECT %s:%s HTTP/1.0\r\n' % client_addr

                user_agent = client.headers.iget('user_agent')
                if not user_agent:
                    user_agent = "User-Agent: restkit/%s\r\n" % __version__

                proxy_pieces = '%s%s%s\r\n' % (proxy_connect, proxy_auth, 
                        user_agent)

                sck = client._manager.find_socket(addr, ssl)
                if sck is None:
                    sck = client.connect(addr, ssl)

                send(sck, proxy_pieces)
                unreader = Unreader(sck)
                resp = Request(unreader)
                body = resp.body.read()
                if resp.status_int != 200:
                    raise ProxyError("Tunnel connection failed: %d %s" %
                            (resp.status_int, body))
                    client._sock = sck
                client._sock_key = (addr, ssl)
            else:
                if proxy_auth:
                    client.headers['Proxy-authorization: %s'] = proxy_auth

                sck = client._manager.find_socket(addr, ssl)
                if sck is None:
                    sck = client.connect(addr, ssl)
                client._sock = sck
                client._sock_key = (addr, ssl)
     
def _get_proxy_auth(proxy_settings):
    proxy_username = os.environ.get('proxy-username')
    if not proxy_username:
        proxy_username = os.environ.get('proxy_username')
    proxy_password = os.environ.get('proxy-password')
    if not proxy_password:
        proxy_password = os.environ.get('proxy_password')

    proxy_password = proxy_password or ""

    if not proxy_username:
        u = urlparse.urlparse(proxy_settings)
        if u.username:
            proxy_password = u.password or proxy_password 
            proxy_settings = urlparse.urlunparse((u.scheme, 
                u.netloc.split("@")[-1], u.path, u.params, u.query, 
                u.fragment))
    
    if proxy_username:
        user_auth = base64.encodestring('%s:%s' % (proxy_username,
                                    proxy_password))
        return proxy_settings, 'Basic %s\r\n' % (user_auth.strip())
    else:
        return proxy_settings, ''

def validate_consumer(consumer):
    """ validate a consumer agains oauth2.Consumer object """
    if not hasattr(consumer, "key"):
        raise ValueError("Invalid consumer.")
    return consumer
    
def validate_token(token):
    """ validate a token agains oauth2.Token object """
    if token is not None and not hasattr(token, "key"):
        raise ValueError("Invalid token.")
    return token


class OAuthFilter(object):
    """ oauth filter """

    def __init__(self, path, consumer, token=None, method=None):
        """ Init OAuthFilter
        
        :param path: path or regexp. * mean all path on wicth oauth can be
        applied.
        :param consumer: oauth consumer, instance of oauth2.Consumer
        :param token: oauth token, instance of oauth2.Token
        :param method: oauth signature method
        
        token and method signature are optionnals. Consumer should be an 
        instance of `oauth2.Consumer`, token an  instance of `oauth2.Toke` 
        signature method an instance of `oauth2.SignatureMethod`.

        """
        
        if path.endswith('*'):
            self.match = re.compile("%s.*" % path.rsplit('*', 1)[0])
        else:
            self.match = re.compile("%s$" % path)
        self.consumer = validate_consumer(consumer)
        self.token = validate_token(token)
        self.method = method or SignatureMethod_HMAC_SHA1()
  
    def on_path(self, client):
        path = client.parsed_url.path or "/"
        return (self.match.match(path) is not None)
        
    def on_request(self, client):
        if not self.on_path(client):
            return

        params = {}
        form = False
        parsed_url = client.parsed_url

        if client.body and client.body is not None:
            ctype = client.headers.iget('content-ype')
            if ctype is not None and \
                    ctype.startswith('application/x-www-form-urlencoded'):
                # we are in a form try to get oauth params from here
                form = True
                params = dict(parse_qsl(client.body))
            
        # update params from quey parameters    
        params.update(parse_qsl(parsed_url.query))
      
        raw_url = urlunparse((parsed_url.scheme, parsed_url.netloc,
                parsed_url.path, '', '', ''))
        
        oauth_req = Request.from_consumer_and_token(self.consumer, 
                        token=self.token, http_method=client.method, 
                        http_url=raw_url, parameters=params)
                    
        oauth_req.sign_request(self.method, self.consumer, self.token)
        
        if form:
            client.body = oauth_req.to_postdata()
            client.headers['Content-Length'] = len(client.body)
        elif client.method in ('GET', 'HEAD'):
            client.original_url = client.url
            client.url = oauth_req.to_url()
        else:
            oauth_headers = oauth_req.to_header()
            client.headers.update(oauth_headers)
