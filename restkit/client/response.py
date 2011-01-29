# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from ..errors import AlreadyRead


class BodyWrapper(object):

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is None:
            return
    
    def __iter__(self):
        return self

    def next(self):
        return self.body.next()

    def read(self, size=None):
        return self.body.read(size=size)

    def readline(self, size=None):
        return self.body.readline(size=size)

    def readlines(self, size=None):
        return self.body.readlines(size=size)


class HttpResponse(object):
    """ Http Response object returned by HttpConnction"""
    
    charset = "utf8"
    unicode_errors = 'strict'
    
    def __init__(self, response, final_url):
        self.response = response
        self.status = response.status
        self.status_int = response.status_int
        self.version = response.version
        self.headerslist = response.headers
        self.final_url = final_url
        
        headers = {}
        for key, value in response.headers:
            headers[key.lower()] = value
        self.headers = headers
        self.closed = False
            
    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            pass
        return self.headers[key.lower()]
    
    def __contains__(self, key):
        return (key.lower() in self.headers)

    def __iter__(self):
        for item in list(self.headers.items()):
            yield item
            
    def body_string(self, charset=None, unicode_errors="strict"):
        """ return body string, by default in bytestring """
        if self.closed or self.response.body.closed:
            raise AlreadyRead("The response have already been read")
        body = self.response.body.read()
        if charset is not None:
            try:
                body = body.decode(charset, unicode_errors)
            except UnicodeDecodeError:
                pass
        return body
        
    def body_stream(self):
        """ return full body stream """
        if self.closed or self.response.body.closed:
            raise AlreadyRead("The response have already been read")
        return BodyWrapper(self.response.body)
        
    def close(self):
        """ release the socket """
        self.closed = True
