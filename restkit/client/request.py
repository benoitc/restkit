# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import copy
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
from restkit.client.response import HttpResponse
from restkit.errors import RequestError, InvalidUrl, RedirectLimit
from restkit.filters import Filters
from restkit.forms import multipart_form_encode, form_encode
from restkit.util import sock
from restkit import util
from restkit import http

MAX_FOLLOW_REDIRECTS = 5

USER_AGENT = "restkit/%s" % __version__

log = logging.getLogger(__name__)

class HttpRequest(object):
    """ Http Connection object. """
    
    version = (1, 1)
    response_class = HttpResponse
    
    def __init__(self, timeout=sock._GLOBAL_DEFAULT_TIMEOUT, 
            filters=None, follow_redirect=False, force_follow_redirect=False, 
            max_follow_redirect=MAX_FOLLOW_REDIRECTS,
            decompress=True,
            pool_instance=None, response_class=None,
            **ssl_args):
            
        """ HttpRequest constructor
        
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
        self.decompress = decompress
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
        self._sock = None
        if hasattr(self.pool,'clear'):
            self.pool.clear_host((self.host, self.port))
        
    def release_connection(self, address, socket):
        if self.should_close:
            sock.close(self._sock) 
        else:
            self.pool.put(address, self._sock)
        self._sock = None
        
    def parse_url(self, url):
        """ parse url and get host/port"""
        self.uri = urlparse.urlparse(url)
        if self.uri.scheme not in ('http', 'https'):
            raise InvalidUrl("None valid url")
        
        host, port = util.parse_netloc(self.uri)
        self.host = host
        self.port = port
        
    def set_body(self, body, headers, chunked=False):
        """ set HTTP body and manage form if needed """
        content_type = headers.get('CONTENT-TYPE')
        content_length = headers.get('CONTENT-LENGTH')
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
            raise RequestError("Can't determine content length and " +
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

        self.init_headers = copy.copy(headers or [])
        self.headers = []
        
        # headers are better as list
        headers = headers  or []
        if isinstance(headers, dict):
            headers = headers.items()
        
        chunked = False
        
        # normalize headers
        search_headers = ('USER-AGENT', 'CONTENT-TYPE',
                'CONTENT-LENGTH', 'ACCEPT-ENCODING',
                'TRANSFER-ENCODING', 'CONNECTION', 'HOST')
        found_headers = {}
        new_headers = copy.copy(headers)
        for (name, value) in headers:
            uname = name.upper()
            if uname in search_headers:
                if uname == 'TRANSFER-ENCODING':
                    if value.lower() == "chunked":
                        chunked = True
                else:
                    found_headers[uname] = value
                    new_headers.remove((name, value))

        self.headers = new_headers
        self.chunked = chunked 
        
        # set body
        self.set_body(body, found_headers, chunked=chunked)

        # force connection close if needed
        if found_headers.get('CONNECTION') == "close":
            self.should_close = True
        elif self.pool is None:
            found_headers['CONNECTION'] = "close" 
        
        self.found_headers = found_headers
        
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


        ua = self.found_headers.get('USER-AGENT')
        accept_encoding = self.found_headers.get('ACCEPT-ENCODING')
        connection = self.found_headers.get('CONNECTION')
        
        # default host header
        try:
            host = self.uri.netloc.encode('ascii')
        except UnicodeEncodeError:
            host = self.uri.netloc.encode('idna')
        host = self.found_headers.get('HOST') or host
        
        # build final request headers
        req_headers = [
            "%s %s %s\r\n" % (self.method, req_path, httpver),
            "Host: %s\r\n" % host,
            "User-Agent: %s\r\n" % ua or USER_AGENT,
            "Accept-Encoding: %s\r\n" % accept_encoding or 'identity'
        ]

        if connection is not None:
            req_headers.append("Connection: %s\r\n" % connection)

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
                self.filters.apply("on_request", self, tries)
                
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
                            errno.ECONNREFUSED, errno.ECONNRESET) or tries <= 0:
                    self.clean_connections()
                    raise
                if e[0] in (errno.EPIPE, errno.ECONNRESET):
                    self.clean_connections()
            except (KeyboardInterrupt, SystemExit):
                break
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
        
        self.release_connection((self.host, self.port), self._sock)
        return self.request(location, self.method, self.body, self.init_headers)
                        
    def start_response(self):
        """
        Get headers, set Body object and return HttpResponse
        """
        # read headers
        release_fun = lambda:self.release_connection(
                        (self.host, self.port), self._sock)
        while True:
            parser = http.ResponseParser(self._sock, 
                        release_source=release_fun,
                        decompress=self.decompress)
            resp = parser.next()
            if resp.status_int != 100:
                break

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
