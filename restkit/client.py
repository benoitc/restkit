# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import copy
import errno
import mimetypes
import os
import threading
import time
import socket
import types
import urlparse
import uuid


try:
    import ssl # python 2.6
    have_ssl = True
except ImportError:
    have_ssl = False

from . import __version__ 
from .datastructures import MultiDict
from .errors import *
from .filters import Filters
from .forms import multipart_form_encode, form_encode
from .globals import _manager
from . import http

from .sock import close, send, sendfile, sendlines, send_chunk
from .tee import TeeInput
from .util import parse_netloc, to_bytestring

MAX_CLIENT_TIMEOUT=300
MAX_CLIENT_CONNECTIONS = 5
MAX_CLIENT_TRIES = 5
CLIENT_WAIT_TRIES = 1.0
MAX_FOLLOW_REDIRECTS = 5
USER_AGENT = "restkit/%s" % __version__


class ClientResponse(object):

    charset = "utf8"
    unicode_errors = 'strict'

    def __init__(self, client, resp):
        

        self.client = client
        self.status = resp.status
        self.status_int = resp.status_int
        self.version = resp.version
        self.headerslist = resp.headers.items()
        self.headers = resp.headers

        self.body = TeeInput(resp, client)

        if client._initial_url:
            self.final_url = url

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            pass
        return self.headers[key.lower()]
    
    def __contains__(self, key):
        return (key.lower() in self.headers)

    def __iter__(self):
        return self.headers.iteritems()

    def body_string(self, charset=None, unicode_errors="strict"):
        """ return body string, by default in bytestring """
        
        # always seek
        self.body.seek(0)

        body = self.body.read()
        if charset is not None:
            try:
                body = body.decode(charset, unicode_errors)
            except UnicodeDecodeError:
                pass
        return body

    def body_stream(self):
         # always seek
        self.body.seek(0)
        return self.body


class Client(object):

    version = (1, 1)
    response_class=ClientResponse

    def __init__(self,
            follow_redirect=False,
            force_follow_redirect=False,
            max_follow_redirect=False,
            filters=None, 
            decompress=True, 
            manager=None,
            response_class=None,
            max_conn=MAX_CLIENT_CONNECTIONS,
            timeout=MAX_CLIENT_TIMEOUT,
            force_dns=False,
            max_tries=5,
            wait_tries=1.0,
            **ssl_args):
        
        self.follow_redirect = follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.max_follow_redirect = max_follow_redirect 
        self.filters = Filters(filters)
        self.decompress = decompress
        
        if manager is None:
            manager = _manager
        self._manager = manager
        if response_class is not None:
            self.response_class =response_class
        self.max_conn = max_conn
        self.max_tries = max_tries
        self.wait_tries = wait_tries
        self.timeout = timeout
        self._connections = {}
        self._url = None
        self._initial_url = None
        self._write_cb = None
        self._headers = None 
        self._sock_key = None
        self._sock = None

        self.req_method = 'GET'
        self.req_body = None

        self.ssl_args = ssl_args or {}
        self._lock = threading.Lock()

    def _headers__get(self):
        if not isinstance(self._headers, MultiDict):
            self._headers = MultiDict(self._headers or [])
        return self._headers
    def _headers__set(self, value):
        self._headers = MultiDict(value)
    req_headers = property(_headers__get, _headers__set, doc=_headers__get.__doc__)
    
    
    def write_callback(self, cb):
        if not callable(cb):
            raise ValueError("%s isn't a callable" % str(cb))
        self._write_cb = cb

    def _url__get(self):
        if self._url is None:
            raise ValueError("url isn't set")
        return urlparse.urlunparse(self._url)
    def _url__set(self, string):
        self._url = urlparse.urlparse(string)
    req_url = property(_url__get, _url__set, doc="current url to request")

    def _host__get(self):
        try:
            host = self._url.netloc.encode('ascii')
        except UnicodeEncodeError:
            host = self._url.netloc.encode('idna')
        
        hdr_host = self.req_headers.iget("host")
        if not hdr_host:
            return host
        return hdr_host
    req_host = property(_host__get, doc="host requested")

    def _path__get(self):
        path = self._url.path or '/'

        return urlparse.urlunparse(('','', path, self._url.params, 
            self._url.query, self._url.fragment))
    req_path = property(_path__get, doc="request path")

    def req_is_chunked(self):
        te = self.req_headers.iget("transfer-encoding")
        return (te is not None and te.lower() == "chunked")

    def req_is_ssl(self):
        if not self._url:
            return False
        return self._url.scheme == "ssl"

    def request(self, url, method='GET', body=None, headers=None):
        self.req_url = url
        self.req_method = method
        self.req_body = body
        self.req_headers = copy.copy(headers) or []
        return self.perform()

    def connect(self, addr, ssl):
        for res in socket.getaddrinfo(addr[0], addr[1], 0, 
                socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res

            try:
                sock = socket.socket(af, socktype, proto)
        
                sock.settimeout(self.timeout)
                sock.connect(sa)
                if ssl:
                    if not have_ssl:
                        raise ValueError("https isn't supported.  On python 2.5x,"
                                        + " https support requires ssl module "
                                        + "(http://pypi.python.org/pypi/ssl) "
                                        + "to be intalled.")
                    validate_ssl_args(self.ssl_args)
                    return ssl.wrap_socket(sock, **self.ssl_args)
                return sock
            except socket.error:
                close(sock)
        raise socket.error, "getaddrinfo returns an empty list" 

    def get_connection(self):
        addr = parse_netloc(self._url)
        
        ssl = self.req_is_ssl()
        self._sock_key = (addr, ssl)
    
        self._lock.acquire()
        try:
            return self._connections.pop(self._sock_key)
        except KeyError:
            sock = self._manager.find_socket(addr, ssl)
            if sock is None:
                sock = self.connect(addr, ssl)
            return sock
        finally:
            self._lock.release()

    def release_connection(self, key, sck):
        self._lock.acquire()
        try:
            if key in self._connections or \
                    len(self._connections) > self.max_conn: 
                self._manager.store_socket(sck, key[0], key[1])
            else:
                self._connections[key] = sck
        finally:
            self._lock.release()

    def close_connection(self):
        close(self._sock)
        self._sock = None

    def parse_body(self):
        if not self.req_body:
            if self.req_method in ('POST', 'PUT',):
                self.req_headers['Content-Length'] = 0
            return

        ctype = self.req_headers.iget('content-type')
        clen = self.req_headers.iget('content-length')
       
        if isinstance(self.req_body, dict):
            if ctype is not None and \
                    ctype.startswith("multipart/form-data"):
                type_, opts = cgi.parse_header(ctype)
                boundary = opts.get('boundary', uuid.uuid4().hex)
                self.req_body, self.req_headers = multipart_form_encode(body, 
                                            self.req_headers, boundary)
            else:
                ctype = "application/x-www-form-urlencoded; charset=utf-8"
                self.req_body = form_encode(self.req_body)
        elif hasattr(self.req_body, "boundary"):
            ctype = "multipart/form-data; boundary=%s" % self.req_body.boundary
            clen = self.req_body.get_size()

        if not ctype:
            ctype = 'application/octet-stream'
            if hasattr(self.req_body, 'name'):
                ctype =  mimetypes.guess_type(self.req_body.name)[0]
        
        if not clen:
            if hasattr(self.req_body, 'fileno'):
                try:
                    self.req_body.flush()
                except IOError:
                    pass
                try:
                    fno = self.req_body.fileno()
                    clen = str(os.fstat(fno)[6])
                except  IOError:
                    if not self.req_is_chunked():
                        clen = len(self.req_body.read())
            elif hasattr(self.req_body, 'getvalue') and not \
                    self.req_is_chunked():
                clen = len(self.req_body.getvalue())
            elif isinstance(self.req_body, types.StringTypes):
                print "ici"
                self.req_body = to_bytestring(self.req_body)
                clen = len(self.req_body)

        if clen is not None:
            self.req_headers['Content-Length'] = clen
        elif not self.req_is_chunked():
            raise RequestError("Can't determine content length and " +
                    "Transfer-Encoding header is not chunked")

        if ctype is not None:
            self.req_headers['Content-Type'] = ctype

    def make_headers_string(self):
        if self.version == (1,1):
            httpver = "HTTP/1.1"
        else:
            httpver = "HTTP/1.0"

        ua = self.req_headers.iget('user_agent')
        host = self.req_host
        accept_encoding = self.req_headers.iget('accept-encoding')

        headers = [
            "%s %s %s\r\n" % (self.req_method, self.req_path, httpver),
            "Host: %s\r\n" % host,
            "User-Agent: %s\r\n" % ua or USER_AGENT,
            "Accept-Encoding: %s\r\n" % accept_encoding or 'identity'
        ]

 
        headers.extend(["%s: %s\r\n" % (k, str(v)) for k, v in \
                self.req_headers.items() if k.lower() not in \
                ('user-agent', 'host', 'accept-encoding',)])
        return "%s\r\n" % "".join(headers) 

    def perform(self):
        if not self._url:
            raise RequestError("req_url isn't set")
        tries = self.max_tries
        wait = self.wait_tries
        while tries > 0:
            try:
                self.parse_body()
                
                headers_str = self.make_headers_string()
                
                # get or create a connection to the remote host
                self._sock = self.get_connection()

                # send headers
                self._sock.sendall(headers_str)

                chunked = self.req_is_chunked()
                
                # send body
                if self.req_body is not None:
                    if hasattr(self.req_body, 'read'):
                        if hasattr(self.req_body, 'seek'): self.req_body.seek(0)
                        sendfile(self._sock, self.req_body, chunked)
                    elif isinstance(self.req_body, types.StringTypes):
                        send(self._sock, self.req_body, chunked)
                    else:
                        sendlines(self._sock, self.req_body, chunked)
                    if chunked:
                        send_chunk(s, "")

                
                return self.get_response()
            except socket.gaierror, e:
                self.close_connection()
                raise RequestError(str(e))
            except socket.timeout, e:
                self.close_connection()
                if tries <= 0:
                    raise RequestTimeout(str(e))
            except socket.error, e:
                self.close_connection()

                if e[0] not in (errno.EAGAIN, errno.ECONNABORTED, 
                        errno.EPIPE, errno.ECONNREFUSED, 
                        errno.ECONNRESET) or tries <= 0:
                    raise RequestError(str(e))
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception, e:
                # unkown error
                self.close_connection()
                raise RequestError("unknown: '%s'" % str(e))

            # time until we retry.
            time.sleep(wait)
            wait = wait * 2
            tries = tries + 1

    def redirect(self, resp, location):
        if self._initial_url is None:
            self._initial_url = self.req_url
        self.url = location
        resp.body.discard()
        self.perform()

    def get_response(self):
        unreader = http.Unreader(self._sock)

        while True:
            resp = http.Request(unreader)
            if resp.status_int != 100:
                break
        
        location = resp.headers.iget('location')

        if self.follow_redirect:
            if resp.status_int in (301, 302, 307,):
                if self.req_method in ('GET', 'HEAD',) or \
                        self.force_follow_redirect:
                    if hasattr(self.req_body, 'read'):
                        try:
                            self.req_body.seek(0)
                        except AttributeError:
                            raise RequestError("Can't redirect %s to %s "
                                    "because body has already been read"
                                    % (self.req_url, location))
                    return self.redirect(location)

            elif  resp.status_int == 303 and self.req_method in ('GET',
                    'HEAD'):
                return self.redirect(resp, location)

        if self.req_method == "HEAD":
            self.release_connection(self._sock_key, self._sock)

        return self.response_class(self, resp)
