# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import gzip
import socket
import StringIO
import urlparse

from restkit import __version__
from restkit.parser import Parser
from restkit import sock
from restkit import util

MAX_FOLLOW_REDIRECTS = 5

class InvalidUrl(Exception):
    pass


class HttpConnection(object):
    """ Http Connection object. """
    
    
    VERSION = (1, 1)
    USER_AGENT = "restkit/%s" % __version__
    
    def __init__(self, timeout=_GLOBAL_DEFAULT_TIMEOUT, 
            filters=None, follow_redirect=False, force_follow_redirect=False, 
            max_follow_redirect=MAX_FOLLOW_REDIRECTS, key_file=None, 
            cert_file=None, pool_instance=None, socket=None):
        self.socket = socket
        self.timeout = timeout
        self.headers = []
        self.ua = self.USER_AGENT
        self.date = ""
        self.uri = None
        
        self.follow_redirect = follow_redirect
        self.nb_redirections = max_follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.method = 'GET'
        self.body = None
        self.response_body = StringIO.StringIO()
        self.final_uri = None
        
        # build filter lists
        self.filters = filters or []
        self.on_request_filters = []
        self.on_response_filters = []
        for f in self.filters:
            if hasattr(f, 'on_request'):
                self.on_request_filters.append(f)
            if hasattr(f, 'on_response'):
                self.on_response_filters.append(f)
                
        if not pool_instance:
            should_close = True
            self.connections = None
        else:
            self.connections = pool_instance
            should_close = False
        
        self.parser = Parser.parse_response(should_close=should_close)
        
    def make_connection(self):
        """ initate a connection if needed or reuse a socket"""
        addr = (self.host, self.port)
        socket = self.socket or None
        
        # if we defined a pool use it
        if self.connections is not None:
            socket = self.connections.get(addr)
            
        if not socket:
            # pool is empty or we don't use a pool
            if self.uri.scheme == "https":
                socket = sock.connect(addr, self.timeout, True, 
                                self.key_file, self.cert_file)
            else:
                socket = sock.connect(addr, self.timeout)
                
        self.socket = socket
        return socket
        
    def clean_connections(self):
        self.socket = None
        self.connections.clean((self.host, self.port))
        
    def maybe_close(self):
        if not self.socket: return
        if self.parser.should_close:
            sock.close(self.socket)
        self.connection.put((self.host, self.port), self.socket)
        self.socket = None
        
    def parse_url(self, url):
        """ parse url and get host/port"""
        self.uri = urlparse.urlparse(url)
        
        host = uri.netloc
        i = host.rfind(':')
        j = host.rfind(']')         # ipv6 addresses have [...]
        if i > j:
            try:
                port = int(host[i+1:])
            except ValueError:
                raise InvalidURL("nonnumeric port: '%s'" % host[i+1:])
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
        """ make effective request """   
        self.parse_url(self, url)
        self.method = method.upper()
        self.body = body
        headers = headers = or []
        if isinstance(headers, dict):
            headers = list(headers.items())
            
        ua = self.USER_AGENT
        req_date =  http_date()
        normalized_headers = []
        
        for name, value in headers:
            name = util.normalize_name(name)
            if name == "User-Agenr":
                ua = value
            elif name == "Date":
                req_date = date
            else:
                if not isinstance(value, basestring):
                    value = str(value)
                normalized_headers.append((name, value))
                
        self.headers = normalized_headers
        self.ua = ua
        self.date = req_date
        
        for bf in self.on_request_filters:
            bf(self)

        # by default all connections are HTTP/1.1    
        if VERSION == (1,1):
            httpver = "HTTP/1.1"
        else:
            httpver = "HTTP/1.0"

        # build request path
        req_path = urlparse.urlunparse(('','', uri.path, '', uri.query, 
                                uri.fragment))
            
        req_headers.append("%s %s %s\r\n" % (httpver, method, req_path))   
        req_headers.append("User-Agent: %s\r\n" % self.ua)
        req_headers.append("Date: %s\r\n" % self.date)
        for name, value in self.headers:
            req_headers.append("%s: %s\r\n" % (name, value))
        
        for i in range(2):
            sock = self.make_connection(sock)
            try:
                # send request
                sock.sendlines(sock, req_headers)
        
                if body is not None:
                    if hasattr(body, 'read'):
                        sock.sendfile(body)
                    elif isinstance(body, basestring):
                        sock.sendfile(StringIO.StringIO(util.to_bytestring(body)))
                    else:
                        sock.sendlines(body)
                self.start_response()
                break
            except socket.gaierror, e:
                self.clean_connections()
                raise
            except socket.error, e:
                if e[0] not in (errno.EAGAIN, errno.ECONNABORTED):
                    self.clean_connections()
                    raise
                self.socket = None
      
    def follow_redirect(self):
        """ follow redirections if needed"""
        if self.nb_redirection <= 0:
            raise errors.RedirectLimit("Redirection limit is reached")
            
        location = self.parser.headers_dict.get('location')
        new_uri = urlparse.urlparse(location)
        if not new_uri.netloc: # we got a relative url
            absolute_uri = "%s://%s" % (uri.scheme, uri.netloc)
            location = urlparse.urljoin(absolute_uri, new_url)
            
        self.final_uri = location
        self.response_body.read() 
        self.nb_redirections -= 1   
        return self.request(location, self.method, self.body,
                        self.headers)
                        
    def start_response(self):
        """
        Get headers, set Body object and return HttpResponse
        """
        
        # read headers
        buf = ""
        buf = recv(self.socket, util.CHUNK_SIZE)
        i = self.parser.filter_headers(headers, buf)
        if i == -1 and buf:
            while True:
                data = sock.recv(self.socket, util.CHUNK_SIZE)
                if not data: break
                buf += data
                i = self.parser.filter_headers(headers, buf)
                if i != -1: break
                    
        if not self.parser.content_len and not self.parser.is_chunked:
            self.response_body = StringIO.StringIO()
        else:
            self.response_body = tee.TeeInput(self.socket, self.parser, 
                                        buf[i:], maybe_close=self.maybe_close)
            
        for af in self.on_response_filters:
            af(self)
            
        if self.follow_redirect:
            if self.parser.status_int in (301, 302, 307):
                if self.method in ('GET', 'HEAD') or \
                                self.force_follow_redirect:
                    if method not in 'GET', 'HEAD') and \
                        hasattr(self.body, 'seek'):
                            self.body.seek(0)
                    return self.follow_redirect()
            elif self.parser.status_int == 303 and self.method in ('GET', 
                    'HEAD'):
                # only 'GET' is possible with this status
                # according the rfc
                return self.follow_redirect()
        return HttpResponse(self)
        
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
        
        headers = {}
        for key, value in self.http_client.parser.headers_dict:
            headers[key.lower()] = value
        self.headers = headers
        
        encoding = headers.get('content-encoding', None)
        if encoding in ('gzip', 'deflate'):
            self._body = gzip.GzipFile(fileobj=self.http_client.response_body)
        else:
            self._body = self.http_client.response_body
            
    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            pass
        return self.headers[key]
        
    def __getattr__(self, key):
         try:
            getattr(super(HttpResponse, self), key)
        except AttributeError:
            if key in self.headers:
                return self.conf[key]
            raise
    
    def __contains__(self, key):
        return (key in self.headers)

    def __iter__(self):
        for item in list(self.headers.items()):
            yield item
        
    @property
    def body(self):
        """ body in bytestring """
        return self._body.read()
        
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
        body = self._body.read()
        return body.decode(self.charset, self.unicode_errors)
        
        