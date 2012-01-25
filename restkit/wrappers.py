# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import cgi
import copy
import mimetypes
import os
from StringIO import StringIO
import types
import urlparse
import uuid

from restkit.datastructures import MultiDict
from restkit.errors import AlreadyRead, RequestError
from restkit.forms import multipart_form_encode, form_encode
from restkit.tee import ResponseTeeInput
from restkit.util import to_bytestring

class Request(object):

    def __init__(self, url, method='GET', body=None, headers=None):
        headers = headers or []
        self.url = url
        self.initial_url = url
        self.method = method

        self._headers = None
        self._body = None

        self.is_proxied = False

        # set parsed uri
        self.headers = headers
        if body is not None:
            self.body = body

    def _headers__get(self):
        if not isinstance(self._headers, MultiDict):
            self._headers = MultiDict(self._headers or [])
        return self._headers
    def _headers__set(self, value):
        self._headers = MultiDict(copy.copy(value))
    headers = property(_headers__get, _headers__set, doc=_headers__get.__doc__)

    def _parsed_url(self):
        if self.url is None:
            raise ValueError("url isn't set")
        return urlparse.urlparse(self.url)
    parsed_url = property(_parsed_url, doc="parsed url")

    def _path__get(self):
        parsed_url = self.parsed_url
        path = parsed_url.path or '/'

        return urlparse.urlunparse(('','', path, parsed_url.params,
            parsed_url.query, parsed_url.fragment))
    path = property(_path__get)

    def _host__get(self):
        try:
            h = self.parsed_url.netloc.encode('ascii')
        except UnicodeEncodeError:
            h = self.parsed_url.netloc.encode('idna')

        hdr_host = self.headers.iget("host")
        if not hdr_host:
            return h
        return hdr_host
    host = property(_host__get)

    def is_chunked(self):
        te = self.headers.iget("transfer-encoding")
        return (te is not None and te.lower() == "chunked")

    def is_ssl(self):
        return self.parsed_url.scheme == "https"

    def _set_body(self, body):
        ctype = self.headers.ipop('content-type', None)
        clen = self.headers.ipop('content-length', None)

        if isinstance(body, dict):
            if ctype is not None and \
                    ctype.startswith("multipart/form-data"):
                type_, opts = cgi.parse_header(ctype)
                boundary = opts.get('boundary', uuid.uuid4().hex)
                self._body, self.headers = multipart_form_encode(body,
                                            self.headers, boundary)
                # at this point content-type is "multipart/form-data"
                # we need to set the content type according to the
                # correct boundary like
                # "multipart/form-data; boundary=%s" % boundary
                ctype = self.headers.ipop('content-type', None)
            else:
                ctype = "application/x-www-form-urlencoded; charset=utf-8"
                self._body = form_encode(body)
        elif hasattr(body, "boundary") and hasattr(body, "get_size"):
            ctype = "multipart/form-data; boundary=%s" % body.boundary
            clen = body.get_size()
            self._body = body
        else:
            self._body = body

        if not ctype:
            ctype = 'application/octet-stream'
            if hasattr(self.body, 'name'):
                ctype =  mimetypes.guess_type(body.name)[0]

        if not clen:
            if hasattr(self._body, 'fileno'):
                try:
                    self._body.flush()
                except IOError:
                    pass
                try:
                    fno = self._body.fileno()
                    clen = str(os.fstat(fno)[6])
                except  IOError:
                    if not self.is_chunked():
                        clen = len(self._body.read())
            elif hasattr(self._body, 'getvalue') and not \
                    self.is_chunked():
                clen = len(self._body.getvalue())
            elif isinstance(self._body, types.StringTypes):
                self._body = to_bytestring(self._body)
                clen = len(self._body)

        if clen is not None:
            self.headers['Content-Length'] = clen

        # TODO: maybe it's more relevant
        # to check if Content-Type is already set in self.headers
        # before overiding it
        if ctype is not None:
            self.headers['Content-Type'] = ctype

    def _get_body(self):
        return self._body
    body = property(_get_body, _set_body, doc="request body")


class BodyWrapper(object):

    def __init__(self, resp, connection):
        self.resp = resp
        self.body = resp._body
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        self.close()

    def close(self):
        """ release connection """
        self.connection.release(self.resp.should_close)

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.body.next()
        except StopIteration:
            self.close()
            raise

    def read(self, n=-1):
        data = self.body.read(n)
        if not data:
            self.close()
        return data

    def readline(self, limit=-1):
        line = self.body.readline(limit)
        if not line:
            self.close()
        return line

    def readlines(self, hint=None):
        lines = self.body.readlines(hint)
        if self.body.close:
            self.close()
        return lines


class Response(object):

    charset = "utf8"
    unicode_errors = 'strict'

    def __init__(self, connection, request, resp):
        self.request = request
        self.connection = connection

        self._resp = resp

        # response infos
        self.headers = resp.headers()
        self.status = resp.status()
        self.status_int = resp.status_code()
        self.version = resp.version()
        self.headerslist = self.headers.items()
        self.location = self.headers.get('location')
        self.final_url = request.url
        self.should_close = not resp.should_keep_alive()


        self._closed = False
        self._already_read = False

        if request.method == "HEAD":
            """ no body on HEAD, release the connection now """
            self.connection.release()
            self._body = StringIO("")
        else:
            self._body = resp.body_file()

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            pass
        return self.headers.get(key)

    def __contains__(self, key):
        return key in self.headers

    def __iter__(self):
        return self.headers.iteritems()

    def can_read(self):
        return not self._already_read

    def body_string(self, charset=None, unicode_errors="strict"):
        """ return body string, by default in bytestring """

        if not self.can_read():
            raise AlreadyRead()


        body = self._body.read()
        self._already_read = True

        # release connection
        self.connection.release(self.should_close)

        if charset is not None:
            try:
                body = body.decode(charset, unicode_errors)
            except UnicodeDecodeError:
                pass
        return body

    def body_stream(self):
        """ stream body """
        if not self.can_read():
            raise AlreadyRead()

        self._already_read = True

        return BodyWrapper(self, self.connection)


    def tee(self):
        """ copy response input to standard output or a file if length >
        sock.MAX_BODY. This make possible to reuse it in your
        appplication. When all the input has been read, connection is
        released """
        return ResponseTeeInput(self, self.connection,
                should_close=self.should_close)
ClientResponse = Response
