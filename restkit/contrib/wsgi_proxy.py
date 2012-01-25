# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from restkit.client import Client
from restkit.conn import MAX_BODY
from restkit.util import rewrite_location

ALLOWED_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']

BLOCK_SIZE = 4096 * 16

WEBOB_ERROR = ("Content-Length is set to -1. This usually mean that WebOb has "
        "already parsed the content body. You should set the Content-Length "
        "header to the correct value before forwarding your request to the "
        "proxy: ``req.content_length = str(len(req.body));`` "
        "req.get_response(proxy)")

class Proxy(object):
    """A proxy wich redirect the request to SERVER_NAME:SERVER_PORT
    and send HTTP_HOST header"""

    def __init__(self, manager=None, allowed_methods=ALLOWED_METHODS,
            strip_script_name=True,  **kwargs):
        self.allowed_methods = allowed_methods
        self.strip_script_name = strip_script_name
        self.client = Client(**kwargs)

    def extract_uri(self, environ):
        port = None
        scheme = environ['wsgi.url_scheme']
        if 'SERVER_NAME' in environ:
            host = environ['SERVER_NAME']
        else:
            host = environ['HTTP_HOST']
        if ':' in host:
            host, port = host.split(':')

        if not port:
            if 'SERVER_PORT' in environ:
                port = environ['SERVER_PORT']
            else:
                port = scheme == 'https' and '443' or '80'

        uri = '%s://%s:%s' % (scheme, host, port)
        return uri

    def __call__(self, environ, start_response):
        method = environ['REQUEST_METHOD']
        if method not in self.allowed_methods:
            start_response('403 Forbidden', ())
            return ['']

        if self.strip_script_name:
            path_info = ''
        else:
            path_info = environ['SCRIPT_NAME']
        path_info += environ['PATH_INFO']

        query_string = environ['QUERY_STRING']
        if query_string:
            path_info += '?' + query_string

        host_uri = self.extract_uri(environ)
        uri = host_uri + path_info

        new_headers = {}
        for k, v in environ.items():
            if k.startswith('HTTP_'):
                k = k[5:].replace('_', '-').title()
                new_headers[k] = v

        for k, v in (('CONTENT_TYPE', None), ('CONTENT_LENGTH', '0')):
            v = environ.get(k, None)
            if v is not None:
                new_headers[k.replace('_', '-').title()] = v

        if new_headers.get('Content-Length', '0') == '-1':
            raise ValueError(WEBOB_ERROR)

        response = self.client.request(uri, method, body=environ['wsgi.input'],
                headers=new_headers)

        if 'location' in response:
            if self.strip_script_name:
                prefix_path = environ['SCRIPT_NAME']

            new_location = rewrite_location(host_uri, response.location,
                    prefix_path=prefix_path)

            headers = []
            for k, v in response.headerslist:
                if k.lower() == 'location':
                    v = new_location
                headers.append((k, v))
        else:
            headers = response.headerslist

        start_response(response.status, headers)

        if method == "HEAD":
            return StringIO()

        return response.tee()

class TransparentProxy(Proxy):
    """A proxy based on HTTP_HOST environ variable"""

    def extract_uri(self, environ):
        port = None
        scheme = environ['wsgi.url_scheme']
        host = environ['HTTP_HOST']
        if ':' in host:
            host, port = host.split(':')

        if not port:
            port = scheme == 'https' and '443' or '80'

        uri = '%s://%s:%s' % (scheme, host, port)
        return uri


class HostProxy(Proxy):
    """A proxy to redirect all request to a specific uri"""

    def __init__(self, uri, **kwargs):
        super(HostProxy, self).__init__(**kwargs)
        self.uri = uri.rstrip('/')
        self.scheme, self.net_loc = urlparse.urlparse(self.uri)[0:2]

    def extract_uri(self, environ):
        environ['HTTP_HOST'] = self.net_loc
        return self.uri

def get_config(local_config):
    """parse paste config"""
    config = {}
    allowed_methods = local_config.get('allowed_methods', None)
    if allowed_methods:
        config['allowed_methods'] = [m.upper() for m in allowed_methods.split()]
    strip_script_name = local_config.get('strip_script_name', 'true')
    if strip_script_name.lower() in ('false', '0'):
        config['strip_script_name'] = False
    config['max_connections'] = int(local_config.get('max_connections', '5'))
    return config

def make_proxy(global_config, **local_config):
    """TransparentProxy entry_point"""
    config = get_config(local_config)
    print 'Running TransparentProxy with %s' % config
    return TransparentProxy(**config)

def make_host_proxy(global_config, uri=None, **local_config):
    """HostProxy entry_point"""
    uri = uri.rstrip('/')
    config = get_config(local_config)
    print 'Running HostProxy on %s with %s' % (uri, config)
    return HostProxy(uri, **config)
