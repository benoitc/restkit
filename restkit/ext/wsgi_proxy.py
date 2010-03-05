# -*- coding: utf-8 -*-
from restkit import ConnectionPool
from restkit import request
from restkit import ResourceNotFound
from restkit.sock import CHUNK_SIZE

ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'DELETE']

class IterBody(object):

    def __init__(self, response):
        self.response = response
        self.length = int(self.response.headers['content-length'])
        self.read = 0

    def __iter__(self):
        return self

    def next(self):
        if self.read >= self.length:
            raise StopIteration
        elif self.read + CHUNK_SIZE > self.length:
            size = self.length - self.read
            self.read = self.length
            return self.response.body_file.read(size)
        else:
            self.read += CHUNK_SIZE
            return self.response.body_file.read(CHUNK_SIZE)

    def close(self):
        pass

class Proxy(object):

    def __init__(self, pool=None, allowed_methods=ALLOWED_METHODS, **kwargs):
        self.pool = pool or ConnectionPool(**kwargs)
        self.allowed_methods = allowed_methods

    def extract_uri(self, environ):
        port = None
        scheme = environ.get('wsgi.url_scheme', 'http')
        host = environ['HTTP_HOST']
        if ':' in host:
            host, port = host.split(':')

        if not port:
            port = scheme == 'https' and '443' or '80'

        uri = '%s://%s:%s' % (scheme, host, port)
        return uri

    def __call__(self, environ, start_response):
        method = environ['REQUEST_METHOD']
        if method not in self.allowed_methods:
            start_response('403 Forbidden', ())
            return ['']

        new_headers = {}
        for k, v in environ.items():
            if k.startswith('HTTP_') and k not in ('HTTP_CONNECTION', 'PROXY_CONNECTION'):
                splited = k.split('_')[1:]
                k = '-'.join([part.title() for part in splited])
                new_headers[k] = v

        if method in ('POST', 'PUT'):
            body = environ['wsgi.input'].read()
        else:
            body=None

        path_info = environ['PATH_INFO']
        query_string = environ['QUERY_STRING']
        if query_string:
            path_info += '?' + query_string

        response = request(self.extract_uri(environ)+path_info, method,
                           body=body, headers=new_headers,
                           pool_instance=self.pool)

        start_response(response.status, response.http_client.parser.headers)

        if 'content-length' in response:
            return IterBody(response)
        else:
            return [response.body]

class HostProxy(Proxy):

    def __init__(self, uri=None, **kwargs):
        super(HostProxy, self).__init__(**kwargs)
        self.uri = uri.lstrip('/')

    def extract_uri(self, environ):
        return self.uri

def make_proxy(global_config, **local_config):
    return Proxy(max_connections=20)

def make_host_proxy(global_config, **local_config):
    return HostProxy(max_connections=20, **local_config)

