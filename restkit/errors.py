# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
exception classes.
"""
            
class ResourceError(Exception):
    """ default error class """
    
    status_int = None
    
    def __init__(self, msg=None, http_code=None, response=None):
        self.msg = msg or ''
        self.status_int = http_code or self.status_int
        self.response = response
        Exception.__init__(self)
        
    def _get_message(self):
        return self.msg
    def _set_message(self, msg):
        self.msg = msg or ''
    message = property(_get_message, _set_message)    
    
    def __str__(self):
        if self.msg:
            return self.msg
        try:
            return str(self.__dict__)
        except (NameError, ValueError, KeyError), e:
            return 'Unprintable exception %s: %s' \
                % (self.__class__.__name__, str(e))
                

class ResourceNotFound(ResourceError):
    """Exception raised when no resource was found at the given url. 
    """
    status_int = 404

class Unauthorized(ResourceError):
    """Exception raised when an authorization is required to access to
    the resource specified.
    """

class ResourceGone(ResourceError):
    """
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.11
    """
    status_int = 410

class RequestFailed(ResourceError):
    """Exception raised when an unexpected HTTP error is received in response
    to a request.
    

    The request failed, meaning the remote HTTP server returned a code 
    other than success, unauthorized, or NotFound.

    The exception message attempts to extract the error

    You can get the status code by e.http_code, or see anything about the 
    response via e.response. For example, the entire result body (which is 
    probably an HTML error page) is e.response.body.
    """
    
class RedirectLimit(Exception):
    """Exception raised when the redirection limit is reached."""

class RequestError(Exception):
    """Exception raised when a request is malformed"""

class RequestTimeout(Exception):
    """ Exception raised on socket timeout """
    
class InvalidUrl(Exception):
    """
    Not a valid url for use with this software.
    """
    
class ResponseError(Exception):
    """ Error raised while getting response or decompressing response stream"""
    

class ProxyError(Exception):
    """ raised when proxy error happend"""
    
class BadStatusLine(Exception):
    """ Exception returned by the parser when the status line is invalid"""
    pass

class ParserError(Exception):
    """ Generic exception returned by the parser """
    pass
    
class UnexpectedEOF(Exception):
    """ exception raised when remote closed the connection """
    
class AlreadyRead(Exception):
    """ raised when a response have already been read """
    
class ProxyError(Exception):
    pass 
    
#############################
# HTTP parser errors
#############################

class ParseException(Exception):
    pass

class NoMoreData(ParseException):
    def __init__(self, buf=None):
        self.buf = buf
    def __str__(self):
        return "No more data after: %r" % self.buf

class InvalidRequestLine(ParseException):
    def __init__(self, req):
        self.req = req
        self.code = 400

    def __str__(self):
        return "Invalid HTTP request line: %r" % self.req

class InvalidRequestMethod(ParseException):
    def __init__(self, method):
        self.method = method

    def __str__(self):
        return "Invalid HTTP method: %r" % self.method
        
class InvalidHTTPVersion(ParseException):
    def __init__(self, version):
        self.version = version
        
    def __str__(self):
        return "Invalid HTTP Version: %s" % self.version
        
class InvalidHTTPStatus(ParseException):
    def __init__(self, status):
        self.status = status
        
    def __str__(self):
        return "Invalid HTTP Status: %s" % self.status

class InvalidHeader(ParseException):
    def __init__(self, hdr):
        self.hdr = hdr
    
    def __str__(self):
        return "Invalid HTTP Header: %r" % self.hdr

class InvalidHeaderName(ParseException):
    def __init__(self, hdr):
        self.hdr = hdr

    def __str__(self):
        return "Invalid HTTP header name: %r" % self.hdr

class InvalidChunkSize(ParseException):
    def __init__(self, data):
        self.data = data
    
    def __str__(self):
        return "Invalid chunk size: %r" % self.data

class ChunkMissingTerminator(ParseException):
    def __init__(self, term):
        self.term = term
    
    def __str__(self):
        return "Invalid chunk terminator is not '\\r\\n': %r" % self.term

class HeaderLimit(ParseException):
    """ exception raised when we gore more headers than 
    max_header_count
    """
