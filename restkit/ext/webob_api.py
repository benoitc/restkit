# -*- coding: utf-8 -*-
try:
    from webob import Response as BaseResponse
    from webob import Request as BaseRequest
except ImportError:
    raise ImportError('WebOb (http://pypi.python.org/pypi/WebOb) is required')
from StringIO import StringIO
from restkit.ext.wsgi_proxy import Proxy
from restkit import request
import urlparse
import urllib

__doc__ = '''Subclasses of webob.Request who use restkit to get a
webob.Response via restkit.ext.wsgi_proxy.Proxy.

Example::

    >>> req = Request.blank('http://pypi.python.org/pypi/restkit')
    >>> resp = req.get_response()
    >>> print resp #doctest: +ELLIPSIS
    200 OK
    Date: ...
    Transfer-Encoding: chunked
    Content-Type: text/html; charset=utf-8
    Server: Apache/2...
    <BLANKLINE>
    <?xml version="1.0" encoding="UTF-8"?>
    ...
    

'''

PROXY = Proxy(allowed_methods=['GET', 'POST', 'HEAD', 'DELETE', 'PUT', 'PURGE'])

class Method(property):
    def __init__(self, name):
        self.name = name
    def __get__(self, instance, klass):
        if not instance:
            return self
        instance.method = self.name.upper()
        def req(*args, **kwargs):
            return instance.get_response(*args, **kwargs)
        return req


class Request(BaseRequest):
    get = Method('get')
    post = Method('post')
    put = Method('put')
    head = Method('head')
    delete = Method('delete')
    def get_response(self):
        if self.content_length < 0:
            self.content_length = 0
        if self.method in ('DELETE', 'GET'):
            self.body = ''
        elif self.method == 'POST' and self.POST:
            body = urllib.urlencode(self.POST.copy())
            stream = StringIO(body)
            stream.seek(0)
            self.body_file = stream
            self.content_length = stream.len
            if 'form' not in self.content_type:
                self.content_type = 'application/x-www-form-urlencoded'
        self.server_name = self.host
        return BaseRequest.get_response(self, PROXY)

    __call__ = get_response

    def set_url(self, url_or_path):
        path = url_or_path.lstrip('/')
        if '?' in path:
            path, self.query_string = path.split('?', 1)
        if path.startswith('http'):
            url = path
        else:
            self.path_info = '/'+path
            url = self.url
        self.scheme, self.host, self.path_info = urlparse.urlparse(url)[0:3]

