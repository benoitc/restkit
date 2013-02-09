# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.
import base64
import errno
import logging
import os
import time
import socket
import ssl
import traceback
import types
import urlparse

try:
    from http_parser.http import (
            HttpStream, BadStatusLine, NoMoreData
    )
    from http_parser.reader import SocketReader
except ImportError:
    raise ImportError("""http-parser isn't installed or out of data.

        pip install http-parser""")

from restkit import __version__

from restkit.conn import Connection
from restkit.errors import RequestError, RequestTimeout, RedirectLimit, \
ProxyError
from restkit.session import get_session
from restkit.util import parse_netloc, rewrite_location, to_bytestring
from restkit.wrappers import Request, Response

MAX_CLIENT_TIMEOUT=300
MAX_CLIENT_CONNECTIONS = 5
MAX_CLIENT_TRIES =3
CLIENT_WAIT_TRIES = 0.3
MAX_FOLLOW_REDIRECTS = 5
USER_AGENT = "restkit/%s" % __version__

log = logging.getLogger(__name__)

class Client(object):
    """A client handle a connection at a time. A client is threadsafe,
    but an handled shouldn't be shared between threads. All connections
    are shared between threads via a pool.
    ::

        >>> from restkit import *
        >>> c = Client()
        >>> r = c.request("http://google.com")
        >>> r.status
        '301 Moved Permanently'
        >>> r.body_string()
        '<HTML><HEAD><meta http-equiv="content-type [...]'
        >>> c.follow_redirect = True
        >>> r = c.request("http://google.com")
        >>> r.status
        '200 OK'
    """

    version = (1, 1)
    response_class=Response

    def __init__(self,
            follow_redirect=False,
            force_follow_redirect=False,
            max_follow_redirect=MAX_FOLLOW_REDIRECTS,
            filters=None,
            decompress=True,
            max_status_line_garbage=None,
            max_header_count=0,
            pool=None,
            response_class=None,
            timeout=None,
            use_proxy=False,
            max_tries=3,
            wait_tries=0.3,
            pool_size=10,
            backend="thread",
            **ssl_args):
        """
        Client parameters
        ~~~~~~~~~~~~~~~~~

        - follow_redirect: follow redirection, by default False
        - max_ollow_redirect: number of redirections available
        - filters: http filters to pass
        - decompress: allows the client to decompress the response body
        - max_status_line_garbage: defines the maximum number of ignorable
          lines before we expect a HTTP response's status line. With HTTP/1.1
          persistent connections, the problem arises that broken scripts could
          return a wrong Content-Length (there are more bytes sent than
          specified).  Unfortunately, in some cases, this cannot be detected
          after the bad response, but only before the next one. So the client
          is abble to skip bad lines using this limit. 0 disable garbage
          collection, None means unlimited number of tries.
        - max_header_count:  determines the maximum HTTP header count allowed.
          by default no limit.
        - pool: the pool to use inherited from socketpool.Pool. By default we
          use the global one.
        - response_class: the response class to use
        - timeout: the default timeout of the connection (SO_TIMEOUT)
        - max_tries: the number of tries before we give up a
        connection
        - wait_tries: number of time we wait between each tries.
        - pool_size: int, default 10. Maximum number of connections we keep in
          the default pool.
        - ssl_args: named argument, see ssl module for more informations
        """
        self.follow_redirect = follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.max_follow_redirect = max_follow_redirect
        self.decompress = decompress
        self.filters = filters or []
        self.max_status_line_garbage = max_status_line_garbage
        self.max_header_count = max_header_count
        self.use_proxy = use_proxy

        self.request_filters = []
        self.response_filters = []
        self.load_filters()


        # set manager

        session_options = dict(
                retry_delay=wait_tries,
                max_size = pool_size,
                retry_max = max_tries,
                timeout = timeout)


        if pool is None:
            pool = get_session(backend, **session_options)
        self._pool = pool
        self.backend = backend

        # change default response class
        if response_class is not None:
            self.response_class = response_class

        self.max_tries = max_tries
        self.wait_tries = wait_tries
        self.pool_size = pool_size
        self.timeout = timeout

        self._nb_redirections = self.max_follow_redirect
        self._url = None
        self._initial_url = None
        self._write_cb = None
        self._headers = None
        self._sock_key = None
        self._sock = None
        self._original = None

        self.method = 'GET'
        self.body = None
        self.ssl_args = ssl_args or {}

    def load_filters(self):
        """ Populate filters from self.filters.
        Must be called each time self.filters is updated.
        """
        for f in self.filters:
            if hasattr(f, "on_request"):
                self.request_filters.append(f)
            if hasattr(f, "on_response"):
                self.response_filters.append(f)



    def get_connection(self, request):
        """ get a connection from the pool or create new one. """

        addr = parse_netloc(request.parsed_url)
        is_ssl = request.is_ssl()

        extra_headers = []
        conn = None
        if self.use_proxy:
            conn = self.proxy_connection(request,
                    addr, is_ssl)
        if not conn:
            conn = self._pool.get(host=addr[0], port=addr[1],
                    pool=self._pool, is_ssl=is_ssl,
                    extra_headers=extra_headers, **self.ssl_args)


        return conn

    def proxy_connection(self, request, req_addr, is_ssl):
        """ do the proxy connection """
        proxy_settings = os.environ.get('%s_proxy' %
                request.parsed_url.scheme)

        if proxy_settings and proxy_settings is not None:
            request.is_proxied = True

            proxy_settings, proxy_auth =  _get_proxy_auth(proxy_settings)
            addr = parse_netloc(urlparse.urlparse(proxy_settings))

            if is_ssl:
                if proxy_auth:
                    proxy_auth = 'Proxy-authorization: %s' % proxy_auth
                proxy_connect = 'CONNECT %s:%s HTTP/1.0\r\n' % req_addr

                user_agent = request.headers.iget('user_agent')
                if not user_agent:
                    user_agent = "User-Agent: restkit/%s\r\n" % __version__

                proxy_pieces = '%s%s%s\r\n' % (proxy_connect, proxy_auth,
                        user_agent)

                conn = self._pool.get(host=addr[0], port=addr[1],
                    pool=self._pool, is_ssl=is_ssl,
                    extra_headers=[], proxy_pieces=proxy_pieces, **self.ssl_args)
            else:
                headers = []
                if proxy_auth:
                    headers = [('Proxy-authorization', proxy_auth)]

                conn = self._pool.get(host=addr[0], port=addr[1],
                        pool=self._pool, is_ssl=False,
                        extra_headers=[], **self.ssl_args)
            return conn

        return

    def make_headers_string(self, request, extra_headers=None):
        """ create final header string """
        headers = request.headers.copy()
        if extra_headers is not None:
            for k, v in extra_headers:
                headers[k] = v

        if not request.body and request.method in ('POST', 'PUT',):
            headers['Content-Length'] = 0

        if self.version == (1,1):
            httpver = "HTTP/1.1"
        else:
            httpver = "HTTP/1.0"

        ua = headers.iget('user-agent')
        if not ua:
            ua = USER_AGENT
        host = request.host

        accept_encoding = headers.iget('accept-encoding')
        if not accept_encoding:
            accept_encoding = 'identity'

        if request.is_proxied:
            full_path = ("https://" if request.is_ssl() else "http://") + request.host + request.path
        else:
            full_path = request.path

        lheaders = [
            "%s %s %s\r\n" % (request.method, full_path, httpver),
            "Host: %s\r\n" % host,
            "User-Agent: %s\r\n" % ua,
            "Accept-Encoding: %s\r\n" % accept_encoding
        ]

        lheaders.extend(["%s: %s\r\n" % (k, str(v)) for k, v in \
                headers.items() if k.lower() not in \
                ('user-agent', 'host', 'accept-encoding',)])
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Send headers: %s" % lheaders)
        return "%s\r\n" % "".join(lheaders)

    def perform(self, request):
        """ perform the request. If an error happen it will first try to
        restart it """

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Start to perform request: %s %s %s" %
                    (request.host, request.method, request.path))
        tries = 0
        while True:
            conn = None
            try:
                # get or create a connection to the remote host
                conn = self.get_connection(request)

                # send headers
                msg = self.make_headers_string(request,
                        conn.extra_headers)

                # send body
                if request.body is not None:
                    chunked = request.is_chunked()
                    if request.headers.iget('content-length') is None and \
                            not chunked:
                        raise RequestError(
                                "Can't determine content length and " +
                                "Transfer-Encoding header is not chunked")


                    # handle 100-Continue status
                    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec8.html#sec8.2.3
                    hdr_expect = request.headers.iget("expect")
                    if hdr_expect is not None and \
                            hdr_expect.lower() == "100-continue":
                        conn.send(msg)
                        msg = None
                        p = HttpStream(SocketReader(conn.socket()), kind=1,
                                decompress=True)


                        if p.status_code != 100:
                            self.reset_request()
                            if log.isEnabledFor(logging.DEBUG):
                                log.debug("return response class")
                            return self.response_class(conn, request, p)

                    chunked = request.is_chunked()
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("send body (chunked: %s)" % chunked)


                    if isinstance(request.body, types.StringTypes):
                        if msg is not None:
                            conn.send(msg + to_bytestring(request.body),
                                    chunked)
                        else:
                            conn.send(to_bytestring(request.body), chunked)
                    else:
                        if msg is not None:
                            conn.send(msg)

                        if hasattr(request.body, 'read'):
                            if hasattr(request.body, 'seek'):
                                request.body.seek(0)
                            conn.sendfile(request.body, chunked)
                        else:
                            conn.sendlines(request.body, chunked)
                    if chunked:
                        conn.send_chunk("")
                else:
                    conn.send(msg)

                return self.get_response(request, conn)
            except socket.gaierror, e:
                if conn is not None:
                    conn.release(True)
                raise RequestError(str(e))
            except socket.timeout, e:
                if conn is not None:
                    conn.release(True)
                raise RequestTimeout(str(e))
            except socket.error, e:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("socket error: %s" % str(e))
                if conn is not None:
                    conn.close()

                errors = (errno.EAGAIN, errno.EPIPE, errno.EBADF,
                        errno.ECONNRESET)
                if e[0] not in errors or tries >= self.max_tries:
                    raise RequestError("socket.error: %s" % str(e))

                # should raised an exception in other cases
                request.maybe_rewind(msg=str(e))

            except NoMoreData, e:
                if conn is not None:
                    conn.release(True)

                request.maybe_rewind(msg=str(e))
                if tries >= self.max_tries:
                    raise
            except BadStatusLine:

                if conn is not None:
                    conn.release(True)

                # should raised an exception in other cases
                request.maybe_rewind(msg="bad status line")

                if tries >= self.max_tries:
                    raise
            except Exception:
                # unkown error
                log.debug("unhandled exception %s" %
                        traceback.format_exc())
                if conn is not None:
                    conn.release(True)

                raise
            tries += 1
            self._pool.backend_mod.sleep(self.wait_tries)

    def request(self, url, method='GET', body=None, headers=None):
        """ perform immediatly a new request """

        request = Request(url, method=method, body=body,
                headers=headers)

        # apply request filters
        # They are applied only once time.
        for f in self.request_filters:
            ret = f.on_request(request)
            if isinstance(ret, Response):
                # a response instance has been provided.
                # just return it. Useful for cache filters
                return ret

        # no response has been provided, do the request
        self._nb_redirections = self.max_follow_redirect
        return self.perform(request)

    def redirect(self, location, request):
        """ reset request, set new url of request and perform it """
        if self._nb_redirections <= 0:
            raise RedirectLimit("Redirection limit is reached")

        if request.initial_url is None:
            request.initial_url = self.url

        # make sure location follow rfc2616
        location = rewrite_location(request.url, location)

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Redirect to %s" % location)

        # change request url and method if needed
        request.url = location

        self._nb_redirections -= 1

        #perform a new request
        return self.perform(request)

    def get_response(self, request, connection):
        """ return final respons, it is only accessible via peform
        method """
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Start to parse response")

        p = HttpStream(SocketReader(connection.socket()), kind=1,
                decompress=self.decompress)

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Got response: %s %s" % (p.version(), p.status()))
            log.debug("headers: [%s]" % p.headers())

        location = p.headers().get('location')

        if self.follow_redirect:
            should_close = not p.should_keep_alive()
            if p.status_code() in (301, 302, 307,):

                # read full body and release the connection
                p.body_file().read()
                connection.release(should_close)

                if request.method in ('GET', 'HEAD',) or \
                        self.force_follow_redirect:
                    if hasattr(self.body, 'read'):
                        try:
                            self.body.seek(0)
                        except AttributeError:
                            raise RequestError("Can't redirect %s to %s "
                                    "because body has already been read"
                                    % (self.url, location))
                    return self.redirect(location, request)

            elif p.status_code() == 303 and self.method == "POST":
                # read full body and release the connection
                p.body_file().read()
                connection.release(should_close)

                request.method = "GET"
                request.body = None
                return self.redirect(location, request)

        # create response object
        resp = self.response_class(connection, request, p)

        # apply response filters
        for f in self.response_filters:
            f.on_response(resp, request)

        if log.isEnabledFor(logging.DEBUG):
            log.debug("return response class")

        # return final response
        return resp


def _get_proxy_auth(proxy_settings):
    proxy_username = os.environ.get('proxy-username')
    if not proxy_username:
        proxy_username = os.environ.get('proxy_username')
    proxy_password = os.environ.get('proxy-password')
    if not proxy_password:
        proxy_password = os.environ.get('proxy_password')

    proxy_password = proxy_password or ""

    if not proxy_username:
        u = urlparse.urlparse(proxy_settings)
        if u.username:
            proxy_password = u.password or proxy_password
            proxy_settings = urlparse.urlunparse((u.scheme,
                u.netloc.split("@")[-1], u.path, u.params, u.query,
                u.fragment))

    if proxy_username:
        user_auth = base64.encodestring('%s:%s' % (proxy_username,
                                    proxy_password))
        return proxy_settings, 'Basic %s\r\n' % (user_auth.strip())
    else:
        return proxy_settings, ''
