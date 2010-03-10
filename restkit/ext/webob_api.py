# -*- coding: utf-8 -*-
try:
    from webob import Response as BaseResponse
    from webob import Request as BaseRequest
except ImportError:
    raise ImportError('WebOb (http://pypi.python.org/pypi/WebOb) is required')
from cStringIO import StringIO
from restkit import request
import urlparse

__doc__ = '''Subclasses of webob.Request who use restkit to get a webob.Response.

Example::

    >>> req = Request.blank('/')
    >>> req.new_url = 'http://pypi.python.org/pypi/restkit'
    >>> resp = req.get_response()
    >>> print resp #doctest: +ELLIPSIS
    200 OK
    date: ...
    transfer-encoding: chunked
    content-type: text/html; charset=utf-8
    server: Apache/2...

'''

StringIOClass = StringIO().__class__

class Response(BaseResponse):
    def __init__(self, resp=None, req=None):
        BaseResponse.__init__(self)
        del self.content_type
        if req:
            self.app_iter = resp.body_file
            self.headers=resp.headers
            self.status = resp.status
        else:
            req = Request.blank('/')
        self.req = req
    def url(self):
        return self.req.url
    @property
    def body_json(self):
        if json:
            return json.loads(self.body)
        return self.body
    def __repr__(self):
        return '<Response(%s from %r)>' % (self.status, self.req)
    def __str__(self):
        if self.content_length > 300:
            return BaseResponse.__str__(self, skip_body=True)
        return BaseResponse.__str__(self)
    def __call__(self):
        print self


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
    ResponseClass = Response
    get = Method('get')
    post = Method('post')
    put = Method('put')
    head = Method('head')
    delete = Method('delete')
    def get_response(self, *args, **kwargs):
        url = self.url
        stream = None
        for a in args:
            if isinstance(a, StringIOClass):
                stream = a
                a.seek(0)
                continue
            elif isinstance(a, basestring):
                if a.startswith('http'):
                    url = a
                elif a.startswith('/'):
                    url = a
        self.new_url = url

        if stream:
            self.body_file = stream
            self.content_length = stream.len
        elif self.content_length < 0:
            self.content_length = 0

        if self.method in ('DELETE', 'GET'):
            self.body = ''
        if self.method == 'GET' and kwargs:
            for k, v in kwargs.items():
                self.GET[k] = v
        elif self.method == 'POST' and kwargs:
            body = urllib.urlencode(kwargs)
            stream = StringIO(body)
            stream.seek(0)
            self.body_file = stream
            self.content_length = stream.len
            if 'form' not in self.content_type:
                self.content_type = 'application/x-www-form-urlencoded'

        resp = request(self.url, self.method,
                       body=self.body_file, headers=self.headers.items())
        resp = Response(resp, self)
        return resp

    __call__ = get_response

    def _new_url(self, url_or_path):
        path = url_or_path.strip('/')
        if path.startswith('http'):
            url = path
        else:
            self.path_info = '/'+path
            url = self.url
        self.scheme, self.host, self.path_info = urlparse.urlparse(url)[0:3]
    new_url = property(fset=_new_url)

    def __str__(self):
        if self.content_length > 300:
            return BaseRequest.__str__(self, skip_body=True)
        return BaseRequest.__str__(self)
    def __repr__(self):
        return '<Request(%s at %s)>' % (self.method, self.url)



