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


        ctype = environ.get("CONTENT_TYPE")
        if ctype and ctype is not None:
            new_headers['Content-Type'] = ctype

        clen = environ.get('CONTENT_LENGTH')
        te =  environ.get('transfer-encoding', '').lower()
        if not clen and te != 'chunked':
            new_headers['transfer-encoding'] = 'chunked'
        elif clen:
            new_headers['Content-Length'] = clen

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
    return TransparentProxy(**config)

def make_host_proxy(global_config, uri=None, **local_config):
    """HostProxy entry_point"""
    uri = uri.rstrip('/')
    config = get_config(local_config)
    return HostProxy(uri, **config)



# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php


import httplib
import urlparse
import urllib

from paste import httpexceptions
from paste.util.converters import aslist

# Remove these headers from response (specify lower case header
# names):
filtered_headers = (
    'transfer-encoding',
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'upgrade',
)

class PasteLikeProxy(object):

    def __init__(self, address, allowed_request_methods=(),
                 suppress_http_headers=(), stream=False, **kwargs):
        self.address = address
        self.parsed = urlparse.urlsplit(address)
        self.scheme = self.parsed[0].lower()
        self.host = self.parsed[1]
        self.path = self.parsed[2]
        self.allowed_request_methods = [
            x.lower() for x in allowed_request_methods if x]

        self.suppress_http_headers = [
            x.lower() for x in suppress_http_headers if x]

        self.stream = stream
        self.client = Client(**kwargs)

    def __call__(self, environ, start_response):
        if (self.allowed_request_methods and
            environ['REQUEST_METHOD'].lower() not in self.allowed_request_methods):
            return httpexceptions.HTTPBadRequest("Disallowed")(environ, start_response)

        conn = self.client
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                key = key[5:].lower().replace('_', '-')
                if key == 'host' or key in self.suppress_http_headers:
                    continue
                headers[key] = value
        headers['host'] = self.host
        if 'REMOTE_ADDR' in environ:
            headers['x-forwarded-for'] = environ['REMOTE_ADDR']
        if environ.get('CONTENT_TYPE'):
            headers['content-type'] = environ['CONTENT_TYPE']

        if environ.get('CONTENT_LENGTH'):
            if environ['CONTENT_LENGTH'] == '-1':
                # This is a special case, where the content length is basically undetermined
                body = environ['wsgi.input'].read(-1)
                headers['content-length'] = str(len(body))
            else:
                headers['content-length'] = environ['CONTENT_LENGTH'] 
                length = int(environ['CONTENT_LENGTH'])
                body = environ['wsgi.input'].read(length)
        else:
            body = ''

        path_info = urllib.quote(environ['PATH_INFO'])
        if self.path:
            request_path = path_info
            if request_path and request_path[0] == '/':
                request_path = request_path[1:]

            path = urlparse.urljoin(self.path, request_path)
        else:
            path = path_info
        if environ.get('QUERY_STRING'):
            path += '?' + environ['QUERY_STRING']

        res = conn.request(u'%s://%s%s' % (self.scheme, self.host, path),
                           environ['REQUEST_METHOD'],
                           body=body, headers=headers)
        headers_out = parse_headers(res.headerslist, stream=self.stream)

        status = res.status
        start_response(status, headers_out)
        # @@: Default?
        if self.stream:
            # See: http://www.python.org/dev/peps/pep-0333/#handling-the-content-length-header
            body = res.body_stream()
        else:
            body = res.tee()
        return body


def parse_headers(headers_list, stream=False):
    """
    Turn a Message object into a list of WSGI-style headers.
    """
    headers_out = []
    for header, value in headers_list:
        if stream:
            # Suppress 'content-length' header:
            #     - The WSGI server CAN stream the response, if possible
            # See: http://www.python.org/dev/peps/pep-0333/#handling-the-content-length-header
            if header.lower() == 'content-length':
                continue
        if header.lower() not in filtered_headers:
            headers_out.append((header, value))
    return headers_out
