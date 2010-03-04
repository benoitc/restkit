# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import ctypes
import errno
import gzip
import logging
import os
import socket
import StringIO
import urlparse

from restkit import __version__
from restkit.errors import RequestError, InvalidUrl, RedirectLimit
from restkit.parser import Parser
from restkit import sock
from restkit import tee
from restkit import util

MAX_FOLLOW_REDIRECTS = 5

USER_AGENT = "restkit/%s" % __version__

log = logging.getLogger(__name__)

class HttpResponse(object):
    """ Http Response object returned by HttpConnction"""
    
    charset = "utf8"
    unicode_errors = 'strict'
    
    def __init__(self, http_client):
        self.http_client = http_client
        self.status = self.http_client.parser.status
        self.status_int = self.http_client.parser.status_int
        self.version = self.http_client.parser.version
        self.headerslist = self.http_client.parser.headers
        self.final_url = self.http_client.final_url
        
        headers = {}
        for key, value in self.http_client.parser.headers:
            headers[key.lower()] = value
        self.headers = headers
        
        encoding = headers.get('content-encoding', None)
        if encoding in ('gzip', 'deflate'):
            self._body = gzip.GzipFile(fileobj=self.http_client.response_body)
        else:
            self._body = self.http_client.response_body
        self._body_eof = False
            
    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            pass
        return self.headers[key]
    
    def __contains__(self, key):
        return (key in self.headers)

    def __iter__(self):
        for item in list(self.headers.items()):
            yield item
          
    @property
    def body(self):
        """ body in bytestring """
        if self._body_eof:
            self._body.seek(0)
        self._body_eof = True
        ret = self._body.read()
        self._body.seek(0)
        return ret
        
    @property
    def body_file(self):
        """ return body as a file like object"""
        return self._body
        
    @property
    def unicode_body(self):
        """ like body but converted to unicode"""
        if not self.charset:
            raise AttributeError(
            "You cannot access HttpResponse.unicode_body unless charset is set")
        return self.body.decode(self.charset, self.unicode_errors)

class HttpConnection(object):
    """ Http Connection object. """
    
    version = (1, 1)
    response_class = HttpResponse
    
    
    def __init__(self, timeout=sock._GLOBAL_DEFAULT_TIMEOUT, 
            filters=None, follow_redirect=False, force_follow_redirect=False, 
            max_follow_redirect=MAX_FOLLOW_REDIRECTS, key_file=None, 
            cert_file=None, pool_instance=None, socket=None,
            response_class=None):
            
        """ HttpConnection constructor
        
        :param timeout: socket timeout
        :param filters: list, list of http filters. see the doc of http filters 
        for more info
        :param follow_redirect: boolean, by default is false. If true, 
        if the HTTP status is 301, 302 or 303 the client will follow
        the location.
        :param max_follow_redirect: max number of redirection. If max is reached
        the RedirectLimit exception is raised.
        :param key_file: the key fle to use with ssl
        :param cert_file: the cert file to use with ssl
        :param pool_instance: a pool instance inherited from 
        `restkit.pool.PoolInterface`
        :param socket: eventually you can pass your own socket object to 
        the client.
        """
        self.socket = socket
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
        self.response_body = StringIO.StringIO()
        self.final_url = None
        
        # build filter lists
        self.filters = filters or []
        self.request_filters = []
        self.response_filters = []
        self.cert_file = cert_file
        self.key_file = key_file

        for f in self.filters:
            self._add_filter(f)
                
        if not pool_instance:
            self.should_close = True
            self.connections = None
        else:
            self.connections = pool_instance
            self.should_close = False
            
        if response_class is not None:
            self.response_class = response_class
        
    def add_filter(self, f):
        self.filters.append(f)
        self._add_filter(f)
            
    def _add_filter(self, f):
        if hasattr(f, 'on_request'):
            self.request_filters.append(f)
            
        if hasattr(f, 'on_response'):
            self.response_filters.append(f)
            
    def remove_filter(self, f):
        for i, f1 in enumerate(self.filters):
            if f == f1: del self.filters[i]
            
        if hasattr(f, 'on_request'):
            for i, f1 in enumerate(self.request_filters):
                if f == f1: del self.request_filters[i]
                
        if hasattr(f, 'on_response'):
            for i, f1 in enumerate(self.response_filters):
                if f == f1: del self.response_filters[i]   
        
    def make_connection(self):
        """ initate a connection if needed or reuse a socket"""
        addr = (self.host, self.port)
        s = self.socket or None
        
        # if we defined a pool use it
        if self.connections is not None:
            s = self.connections.get(addr)
            
        if not s:
            # pool is empty or we don't use a pool
            if self.uri.scheme == "https":
                s = sock.connect(addr, self.timeout, True, 
                                self.key_file, self.cert_file)
            else:
                s = sock.connect(addr, self.timeout)
                
        self.socket = s
        return s
        
    def clean_connections(self):
        self.socket = None
        if hasattr(self.connections,'clean'):
            self.connections.clean((self.host, self.port))
        
    def maybe_close(self):
        if not self.socket: return
        if self.parser.should_close:
            sock.close(self.socket) 
        else: # release the socket in the pool
            self.connections.put((self.host, self.port), self.socket)
        self.socket = None
        
    def parse_url(self, url):
        """ parse url and get host/port"""
        self.uri = urlparse.urlparse(url)
        if self.uri.scheme not in ('http', 'https'):
            raise InvalidUrl("None valid url")
        
        host = self.uri.netloc
        i = host.rfind(':')
        j = host.rfind(']')         # ipv6 addresses have [...]
        if i > j:
            try:
                port = int(host[i+1:])
            except ValueError:
                raise InvalidUrl("nonnumeric port: '%s'" % host[i+1:])
            host = host[:i]
        else:
            # default por
            if self.uri.scheme == "https":
                port = 443
            else:
                port = 80
                
        if host and host[0] == '[' and host[-1] == ']':
            host = host[1:-1]
            
        self.host = host
        self.port = port
        
    def request(self, url, method='GET', body=None, headers=None):
        """ make effective request 
        
        :param url: str, url string
        :param method: str, by default GET. http verbs
        :param body: the body, could be a string, an iterator or a file-like object
        :param headers: dict or list of tupple, http headers
        """
        self.parser = Parser.parse_response(should_close=self.should_close)
        self.url = url
        self.final_url = url
        self.parse_url(url)
        self.method = method.upper()
        
        
        # headers are better as list
        headers = headers  or []
        if isinstance(headers, dict):
            headers = list(headers.items())
            
        ua = USER_AGENT
        normalized_headers = []
        content_len = None
        accept_encoding = 'identity'
        chunked = False
        
        # default host
        try:
            host = self.uri.netloc.encode('ascii')
        except UnicodeEncodeError:
            host = self.uri.netloc.encode('idna')

        # normalize headers
        for name, value in headers:
            name = util.normalize_name(name)
            if name == "User-Agenr":
                ua = value
            elif name == "Content-Length":
                content_len = str(value)
            elif name == "Accept-Encoding":
                accept_encoding = 'identity'
            elif name == "Host":
                host = value
            elif name == "Transfer-Encoding":
                if value.lower() == "chunked":
                    chunked = True
                normalized_headers.append((name, value))
            else:
                if not isinstance(value, basestring):
                    value = str(value)
                normalized_headers.append((name, value))
        
        # set content lengh if needed
        if body and body is not None:
            if not content_len:
                if hasattr(body, 'fileno'):
                    try:
                        body.flush()
                    except IOError:
                        pass
                    content_len = str(os.fstat(body.fileno())[6])
                elif hasattr(body, 'len'):
                    try:
                        content_len = str(body.len)
                    except AttributeError:
                        pass
                elif isinstance(body, basestring):
                    body = util.to_bytestring(body)
                    content_len = len(body)
            
            if content_len:
                normalized_headers.append(("Content-Length", content_len))
            elif not chunked:
                raise RequestError("Can't determine content length and" +
                        "Transfer-Encoding header is not chunked")
                
        if self.method in ('POST', 'PUT') and not body:
            normalized_headers.append(("Content-Length", "0"))
       
        self.body = body
        self.headers = normalized_headers
        self.ua = ua
        
        # apply on request filters
        for bf in self.request_filters:
            bf.on_request(self)
            
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
        req_headers = []   
        req_headers.append("%s %s %s\r\n" % (method, req_path, httpver))
        req_headers.append("Host: %s\r\n" % host)
        req_headers.append("User-Agent: %s\r\n" % self.ua)
        req_headers.append("Accept-Encoding: %s\r\n" % accept_encoding)
        for name, value in self.headers:
            req_headers.append("%s: %s\r\n" % (name, value))
        req_headers.append("\r\n")
        self.req_headers = req_headers
        
        # Finally do the request
        return self.do_send(req_headers, self.body, chunked)
        
    def do_send(self, req_headers, body=None, chunked=False):
        tries = 2
        while True:
            try:
                s = self.make_connection()
                # send request
                sock.sendlines(s, req_headers)
                
                log.info('Start request: %s %s' % (self.method, self.url))
                log.debug("Request headers: [%s]" % str(req_headers))
                
                if body is not None:
                    if hasattr(body, 'read'):
                        if hasattr(body, 'seek'): body.seek(0)
                        sock.sendfile(s, body, chunked)
                    elif isinstance(body, basestring):
                        sock.sendfile(s, StringIO.StringIO(
                                util.to_bytestring(body)), chunked)
                    else:
                        sock.sendlines(s, body, chunked)
                        
                    if chunked: # final chunk
                        sock.send_chunk(s, "")
                        
                return self.start_response()
            except socket.gaierror, e:
                self.clean_connections()
                raise
            except socket.error, e:
                if e[0] not in (errno.EAGAIN, errno.ECONNABORTED, errno.EPIPE,
                            errno.ECONNREFUSED) or tries <= 0:
                    self.clean_connections()
                    raise
            except:
                if tries <= 0:
                    raise
            tries -= 1
            
      
    def do_redirect(self):
        """ follow redirections if needed"""
        if self.nb_redirections <= 0:
            raise RedirectLimit("Redirection limit is reached")
            
        location = self.parser.headers_dict.get('Location')
        if not location:
            raise RequestError('no Location header')
        
        new_uri = urlparse.urlparse(location)
        if not new_uri.netloc: # we got a relative url
            absolute_uri = "%s://%s" % (self.uri.scheme, self.uri.netloc)
            location = urlparse.urljoin(absolute_uri, location)
          
        log.debug("Redirect to %s" % location)
          
        self.final_url = location
        self.response_body.read() 
        self.nb_redirections -= 1
        self.maybe_close()
        return self.request(location, self.method, self.body,
                        self.headers)
                        
    def start_response(self):
        """
        Get headers, set Body object and return HttpResponse
        """
        # read headers
        headers = []
        buf = sock.recv(self.socket, sock.CHUNK_SIZE)
        i = self.parser.filter_headers(headers, buf)
        if i == -1 and buf:
            while True:
                data = sock.recv(self.socket, sock.CHUNK_SIZE)
                if not data: break
                buf += data
                i = self.parser.filter_headers(headers, buf)
                if i != -1:
                    break
        
        log.debug("Start response: %s" % str(self.parser.status_line))
        log.debug("Response headers: [%s]" % str(headers))
        
        if (not self.parser.content_len and not self.parser.is_chunked):
            response_body = StringIO.StringIO("".join(buf[i:]))
            if self.parser.should_close:
                # http 1.0 or something like it. 
                # we try to get missing body
                log.debug("No content len an not chunked transfer, get body")
                while True:
                    try:
                        chunk = sock.recv(self.socket, sock.CHUNK_SIZE)
                    except socket.error:
                        break
                    if not chunk: break
                    response_body.write("".join(chunk))
                self.maybe_close()
                    
            response_body.seek(0)
            self.response_body = response_body
        elif self.method == "HEAD":
            self.response_body = StringIO.StringIO()
            self.maybe_close()
        else:
            self.response_body = tee.TeeInput(self.socket, self.parser, 
                                        buf[i:], maybe_close=self.maybe_close)
        
        # apply on response filters
        for af in self.response_filters:
            af.on_response(self)

        if self.follow_redirect:
            if self.parser.status_int in (301, 302, 307):
                if self.method in ('GET', 'HEAD') or \
                                self.force_follow_redirect:
                    if self.method not in ('GET', 'HEAD') and \
                        hasattr(self.body, 'seek'):
                            self.body.seek(0)
                    return self.do_redirect()
            elif self.parser.status_int == 303 and self.method in ('GET', 
                    'HEAD'):
                # only 'GET' is possible with this status
                # according the rfc
                return self.do_redirect()
        
               
        self.final_url = self.parser.headers_dict.get('Location', 
                    self.final_url)
        log.debug("Return response: %s" % self.final_url) 
        return self.response_class(self)
        
        