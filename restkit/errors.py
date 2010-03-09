# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
exception classes.
"""
            
class ResourceError(Exception):
    """ default error class """
    def __init__(self, msg=None, http_code=None, response=None):
        self.msg = msg or ''
        self.status_int = http_code
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

class Unauthorized(ResourceError):
    """Exception raised when an authorization is required to access to
    the resource specified.
    """

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
    
class UnexpectedEOF(object):
    """ exception raised when remote closed the connection """