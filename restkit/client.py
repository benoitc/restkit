# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import cgi
import errno
import logging
import mimetypes
import os
import socket
import time
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import types
import urlparse
import uuid

from restkit import __version__
from restkit.errors import RequestError, InvalidUrl, RedirectLimit, \
AlreadyRead
from restkit.filters import Filters
from restkit.forms import multipart_form_encode, form_encode
from restkit.util import sock
from restkit import tee
from restkit import util
from restkit.util.misc import deprecated_property
from restkit import http

MAX_FOLLOW_REDIRECTS = 5

USER_AGENT = "restkit/%s" % __version__

log = logging.getLogger(__name__)

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
        self.close()
        return body
        
    def body_stream(self):
        """ return full body stream """
        if self.closed or self.response.body.closed:
            raise AlreadyRead("The response have already been read")
        return self.response.body
        
    def close(self):
        """ release the socket """
        self.closed = True
        self.response.body.close()
          
    @property
    def body(self):
        """ body in bytestring """
        return self.body_string()
        
    body = deprecated_property(
            body, 'body', 'use body_string() instead',
            warning=True)
        
    @property
    def body_file(self):
        """ return body as a file like object"""
        return self.body_stream()
        
    body_file = deprecated_property(
            body_file, 'body_file', 'use body_stream() instead',
            warning=True)   
        
    @property
    def unicode_body(self):
        """ like body but converted to unicode"""
        if not self.charset:
            raise AttributeError(
            "You cannot access HttpResponse.unicode_body unless charset is set")
        body = self.body_string()
        return body.decode(self.charset, self.unicode_errors)
            
    unicode_body = deprecated_property(
            unicode_body, 'unicode_body', 'replaced by body_string()',
            warning=True)

class HttpConnection(object):
    """ Http Connection object. """
    
    version = (1, 1)
    response_class = HttpResponse
    
    
    def __init__(self, timeout=sock._GLOBAL_DEFAULT_TIMEOUT, 
            filters=None, follow_redirect=False, force_follow_redirect=False, 
            max_follow_redirect=MAX_FOLLOW_REDIRECTS, 
            pool_instance=None, response_class=None,
            **ssl_args):
            
        """ HttpConnection constructor
        
        :param timeout: socket timeout
        :param filters: list, list of http filters. see the doc of http filters 
        for more info
        :param follow_redirect: boolean, by default is false. If true, 
        if the HTTP status is 301, 302 or 303 the client will follow
        the location.
        :param max_follow_redirect: max number of redirection. If max is reached
        the RedirectLimit exception is raised.
        :param pool_instance: a pool instance inherited from 
        `restkit.pool.PoolInterface`
        :param ssl_args: ssl arguments. See http://docs.python.org/library/ssl.html
        for more information.
        """
        self._sock = None
        self.timeout = timeout
        self.headers = []
        self.req_headers = []
        self.ua = USER_AGENT
        self.url = None
        
        self.follow_redirect = follow_redirect
        self.nb_redirections = max_follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.method = 'GET'
        self.body = None
        self.response_body = StringIO()
        self.final_url = None
        
        # build filter lists
        self.filters = Filters(filters)
        self.ssl_args = ssl_args or {}
       
        if not pool_instance:
            self.should_close = True
            self.pool = None
        else:
            self.pool = pool_instance
            self.should_close = False
            
        if response_class is not None:
            self.response_class = response_class
         
    def make_connection(self):
        """ initate a connection if needed or reuse a socket"""
        
        # apply on connect filters
        self.filters.apply("on_connect", self)
        if self._sock is not None:
            return self._sock
        
        addr = (self.host, self.port)
        s = None
        # if we defined a pool use it
        if self.pool is not None:
            s = self.pool.get(addr)
            
        if not s:
            # pool is empty or we don't use a pool
            if self.uri.scheme == "https":
                s = sock.connect(addr, True, self.timeout, **self.ssl_args)
            else:
                s = sock.connect(addr, False, self.timeout)
        return s
        
    def clean_connections(self):
        sock.close(self._sock) 
        if hasattr(self.pool,'clear'):
            self.pool.clear_host((self.host, self.port))
        
    def release_connection(self, address, socket):
        if not self.pool:
            sock.close(self._sock) 
            return
        self.pool.put(address, self._sock)
        
    def parse_url(self, url):
        """ parse url and get host/port"""
        self.uri = urlparse.urlparse(url)
        if self.uri.scheme not in ('http', 'https'):
            raise InvalidUrl("None valid url")
        
        host, port = util.parse_netloc(self.uri)
        self.host = host
        self.port = port
        
    def set_body(self, body, content_type=None, content_length=None, 
            chunked=False):
        """ set HTTP body and manage form if needed """
        if not body:
            if content_type is not None:
                self.headers.append(('Content-Type', content_type))
            if self.method in ('POST', 'PUT'):
                self.headers.append(("Content-Length", "0"))
            return
        
        # set content lengh if needed
        if isinstance(body, dict):
            if content_type is not None and \
                    content_type.startswith("multipart/form-data"):
                type_, opts = cgi.parse_header(content_type)
                boundary = opts.get('boundary', uuid.uuid4().hex)
                body, self.headers = multipart_form_encode(body, 
                                            self.headers, boundary)
            else:
                content_type = "application/x-www-form-urlencoded; charset=utf-8"
                body = form_encode(body)
        elif hasattr(body, "boundary"):
            content_type = "multipart/form-data; boundary=%s" % body.boundary
            content_length = body.get_size()

        if not content_type:
            content_type = 'application/octet-stream'
            if hasattr(body, 'name'):
                content_type = mimetypes.guess_type(body.name)[0]
            
        if not content_length:
            if hasattr(body, 'fileno'):
                try:
                    body.flush()
                except IOError:
                    pass
                content_length = str(os.fstat(body.fileno())[6])
            elif hasattr(body, 'getvalue'):
                try:
                    content_length = str(len(body.getvalue()))
                except AttributeError:
                    pass
            elif isinstance(body, types.StringTypes):
                body = util.to_bytestring(body)
                content_length = len(body)
        
        if content_length:
            self.headers.append(("Content-Length", content_length))
            if content_type is not None:
                self.headers.append(('Content-Type', content_type))
            
        elif not chunked:
            raise RequestError("Can't determine content length and" +
                    "Transfer-Encoding header is not chunked")
            
        self.body = body               
        
        
    def request(self, url, method='GET', body=None, headers=None):
        """ make effective request 
        
        :param url: str, url string
        :param method: str, by default GET. http verbs
        :param body: the body, could be a string, an iterator or a file-like object
        :param headers: dict or list of tupple, http headers
        """
        self._sock = None
        self.url = url
        self.final_url = url
        self.parse_url(url)
        self.method = method.upper()
        self.headers = []
        
        # headers are better as list
        headers = headers  or []
        if isinstance(headers, dict):
            headers = list(headers.items())
            
        ua = USER_AGENT
        content_length = None
        accept_encoding = 'identity'
        chunked = False
        content_type = None
        
        if not self.pool:
            connection = "close"
        else:
            connection = "keep-alive"
        
        # default host
        try:
            host = self.uri.netloc.encode('ascii')
        except UnicodeEncodeError:
            host = self.uri.netloc.encode('idna')

        # normalize headers
        for name, value in headers:
            name = name.title()
            if name == "User-Agent":
                ua = value
            elif name == "Content-Type":
                content_type = value
            elif name == "Content-Length":
                content_length = str(value)
            elif name == "Accept-Encoding":
                accept_encoding = value
            elif name == "Host":
                host = value
            elif name == "Transfer-Encoding":
                if value.lower() == "chunked":
                    chunked = True
                self.headers.append((name, value))
            elif name == "Connection":
                connection = value
            else:
                if not isinstance(value, types.StringTypes):
                    value = str(value)
                self.headers.append((name, value))
                
        self.headers.append(("Connection", connection))
        
        self.set_body(body, content_type=content_type, 
            content_length=content_length, chunked=chunked)

        self.ua = ua
        self.chunked = chunked
        self.host_hdr = host
        self.accept_encoding = accept_encoding
        
        # Finally do the request
        return self.do_send()
        
    def _req_headers(self):
        # by default all connections are HTTP/1.1    
        if self.version == (1,1):
            httpver = "HTTP/1.1"
        else:
            httpver = "HTTP/1.0"

        # request path
        path = self.uri.path or "/"
        req_path = urlparse.urlunparse(('','', path, '', 
                        self.uri.query, self.uri.fragment))
           
        # build final request headers
        req_headers = [
            "%s %s %s\r\n" % (self.method, req_path, httpver),
            "Host: %s\r\n" % self.host_hdr,
            "User-Agent: %s\r\n" % self.ua,
            "Accept-Encoding: %s\r\n" % self.accept_encoding
        ]
        req_headers.extend(["%s: %s\r\n" % (k, v) for k, v in self.headers])
        req_headers.append('\r\n')
        return req_headers
               
    def do_send(self):
        tries = 2
        while True:
            try:
                # get socket
                self._sock = self.make_connection()
                
                # apply on request filters
                self.filters.apply("on_request", self)
                
                # build request headers
                self.req_headers = req_headers = self._req_headers()
                
                # send request
                log.info('Start request: %s %s', self.method, self.url)
                log.debug("Request headers: [%s]", req_headers)
                
                self._sock.sendall("".join(req_headers))
                
                if self.body is not None:
                    if hasattr(self.body, 'read'):
                        if hasattr(self.body, 'seek'): self.body.seek(0)
                        sock.sendfile(self._sock, self.body, self.chunked)
                    elif isinstance(self.body, types.StringTypes):
                        sock.send(self._sock, self.body, self.chunked)
                    else:
                        sock.sendlines(self._sock, self.body, self.chunked)
                        
                    if self.chunked: # final chunk
                        sock.send_chunk(self._sock, "")
                        
                return self.start_response()
            except socket.gaierror, e:
                self.clean_connections()
                raise
            except socket.error, e:
                if e[0] not in (errno.EAGAIN, errno.ECONNABORTED, errno.EPIPE,
                            errno.ECONNREFUSED) or tries <= 0:
                    self.clean_connections()
                    raise
                if e[0] == errno.EPIPE:
                    log.debug("Got EPIPE")
                    self.clean_connections()
            except:
                if tries <= 0:
                    raise
                # we don't know what happend. 
                self.clean_connections()
            time.sleep(0.2)
            tries -= 1
            
      
    def do_redirect(self, response, location):
        """ follow redirections if needed"""
        if self.nb_redirections <= 0:
            raise RedirectLimit("Redirection limit is reached")
            
        if not location:
            raise RequestError('no Location header')
        
        new_uri = urlparse.urlparse(location)
        if not new_uri.netloc: # we got a relative url
            absolute_uri = "%s://%s" % (self.uri.scheme, self.uri.netloc)
            location = urlparse.urljoin(absolute_uri, location)
          
        log.debug("Redirect to %s" % location)
          
        self.final_url = location
        response.body.read() 
        self.nb_redirections -= 1
        sock.close(self._sock)
        return self.request(location, self.method, self.body, self.headers)
                        
    def start_response(self):
        """
        Get headers, set Body object and return HttpResponse
        """
        # read headers
        parser = http.ResponseParser(self._sock, 
                        release_source = lambda:self.release_connection(
                        (self.host, self.port), self._sock))
        resp = parser.next()

        log.debug("Start response: %s", resp.status)
        log.debug("Response headers: [%s]", resp.headers)
        
        location = None
        for hdr_name, hdr_value in resp.headers:
            if hdr_name.lower() == "location":
                location = hdr_value
                break
        
        if self.follow_redirect:
            if resp.status_int in (301, 302, 307):
                if self.method in ('GET', 'HEAD') or \
                                self.force_follow_redirect:
                    if self.method not in ('GET', 'HEAD') and \
                        hasattr(self.body, 'seek'):
                            self.body.seek(0)
                    return self.do_redirect(resp, location)
            elif resp.status_int == 303 and self.method in ('GET', 
                    'HEAD'):
                # only 'GET' is possible with this status
                # according the rfc
                return self.do_redirect(resp, location)

        
        # apply on response filters
        self.filters.apply("on_response", self)

        self.final_url = location or self.final_url
        log.debug("Return response: %s" % self.final_url)
        if self.method == "HEAD":
            resp.body = StringIO()

        return self.response_class(resp, self.final_url)
        
        
