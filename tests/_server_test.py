# -*- coding: utf-8 -
#
# Copyright (c) 2008 (c) Benoit Chesneau <benoitc@e-engura.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import base64
import cgi
try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import io
import os
import select
import socket
import sys
import tempfile
import threading
import unittest

try:
    import http.cookies as Cookie
except ImportError:
    import Cookie


from restkit.py3compat import (PY3, parse_qsl, parse_qs, urlparse, unquote,
        bytes_to_str, str_to_bytes, string_types, BytesIO, StringIO)
from restkit.tee import TeeInput
from restkit.util import to_bytestring

HOST = 'localhost'
PORT = (os.getpid() % 31000) + 1024

if PY3:
    from io import TextIOWrapper
    class NCTextIOWrapper(TextIOWrapper):
        def close(self): pass # Keep wrapped buffer open.

class FieldStorage(cgi.FieldStorage):
    def __nonzero__(self):
        return bool(self.list or self.file)

    def make_file(self, binary=None):
        import tempfile
        return tempfile.TemporaryFile("w+b")


def parse_multipart(fp, headers):
    environ = {'CONTENT_TYPE':
            headers.get('content-type'),'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': headers.get('content-length', '0')}

    sys.stderr.write('got clen %s\n' % headers.get('content-length', 0))
    args = dict(fp=fp, environ=environ, keep_blank_values=True)
    if PY3:
        args['fp'] = NCTextIOWrapper(args['fp'], encoding='ISO-8859-1',
                                         newline='\n')
        args['encoding'] = 'ISO-8859-1'

    sys.stderr.write( "%s\n" % str(args))
    form = FieldStorage(**args)
    post = {}
    for item in (form.list or []):
        post[item.name] = item if item.filename else item.value


    sys.stderr.write("post %s\n\n" % str(post))
    return post


class HTTPTestHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.auth = b'Basic ' + base64.b64encode(str_to_bytes("test:test"))[:-1]
        self.count = 0
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)


    def do_GET(self):
        self.parsed_uri = urlparse(unquote(self.path))
        self.query = {}
        for k, v in parse_qsl(self.parsed_uri[4]):
            self.query[k] = v
        path = self.parsed_uri[2]
        if path == "/":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "welcome")

        elif path == "/unicode":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "éàù@")

        elif path == "/json":
            content_type = self.headers.get('content-type', 'text/plain')
            if content_type != "application/json":
                self.error_Response("bad type")
            else:
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")

        elif path == "/éàù":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "ok")

        elif path == "/test":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "ok")

        elif path == "/query":
            test = self.query.get("test", False)
            if test and test == "testing":
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/qint":
            test = self.query.get("test", False)
            if test and test == "1":
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/auth":
            extra_headers = [('Content-type', 'text/plain')]

            if not 'Authorization' in self.headers:
                realm = "test"
                extra_headers.append(('WWW-Authenticate', 'Basic realm="%s"' % realm))
                self._respond(401, extra_headers, "")
            else:
                auth = str_to_bytes(self.headers['Authorization'][len('Basic')+1:])
                auth = base64.b64decode(auth).split(b':')
                if auth[0] == b"test" and auth[1] == b"test":
                    self._respond(200, extra_headers, "ok")
                else:
                    self._respond(403, extra_headers, "niet!")
        elif path == "/redirect":
            extra_headers = [('Content-type', 'text/plain'),
                ('Location', '/complete_redirect')]
            self._respond(301, extra_headers, "")

        elif path == "/complete_redirect":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "ok")

        elif path == "/redirect_to_url":
            extra_headers = [('Content-type', 'text/plain'),
                ('Location', 'http://localhost:%s/complete_redirect' % PORT)]
            self._respond(301, extra_headers, "")

        elif path == "/pool":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "ok")

        elif path == "/cookie":
            c = Cookie.SimpleCookie()
            c["fig"] = "newton"
            c['fig']['path'] = "/"
            for k in c.keys():
                extra_headers = [('Set-Cookie', str(c[k].output(header='')))]
            self._respond(200, extra_headers, "ok")

        elif path == "/cookies":
            c = Cookie.SimpleCookie()
            c["fig"] = "newton"
            c['fig']['path'] = "/"
            c["sugar"] = "wafer"
            c['sugar']['path'] = "/"
            extra_headers = []
            for k in c.keys():
                extra_headers.append(('Set-Cookie', str(c[k].output(header=''))))
            self._respond(200, extra_headers, "ok")

        else:
            self._respond(404,
                [('Content-type', 'text/plain')], "Not Found" )


    def do_POST(self):
        self.parsed_uri = urlparse(self.path)
        self.query = {}
        for k, v in parse_qsl(self.parsed_uri[4]):
            self.query[k] = v

        path = self.parsed_uri[2]
        import sys
        sys.stderr.write("path %s\n" % path)

        nbytes = int(self.headers.get('content-length') or 0)
        data = self.rfile.read(nbytes)

        req_body = BytesIO(data)

        # throw away additional data [see bug #427345]
        while select.select([self.rfile], [], [], 0)[0]:
            if not self.rfile.read(1):
                break

        extra_headers = []
        if path == "/":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = req_body.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/bytestring":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = req_body.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/unicode":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = req_body.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/json":
            content_type = self.headers.get('content-type', 'text/plain')
            if content_type != "application/json":
                self.error_Response("bad type: %s" % content_type)
            else:
                extra_headers.append(('Content-type', content_type))
                content_length = int(self.headers.get('Content-length', 0))
                body = req_body.read(content_length)
                self._respond(200, extra_headers, body)
        elif path == "/empty":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = req_body.read(content_length)
            if body == "":
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()

        elif path == "/query":
            test = self.query.get("test", False)
            if test and test == "testing":
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/form":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = req_body.read(content_length)
            form = parse_qs(body)
            if form[b'a'] == [b"a"] and form[b"b"] == [b"b"]:
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/multivalueform":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = req_body.read(content_length)
            form = parse_qs(body)
            if form[b'a'] == [b"a", b"c"] and form[b"b"] == [b"b"]:
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/multipart":
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
            content_length = int(self.headers.get('Content-length', '0'))
            if ctype == 'multipart/form-data':
                req = parse_multipart(req_body, self.headers)
                body = req['t'][0]
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, body)
            else:
                self.error_Response()
        elif path == "/multipart2":
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
            content_length = int(self.headers.get('Content-length', '-1'))
            if ctype == 'multipart/form-data':
                req = parse_multipart(req_body, self.headers)
                f = req['f']
                if not req['a'] == ['aa']:
                    self.error_Response()
                if not req['b'] == ['bb','éàù@']:
                    self.error_Response()
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, str(len(f.file.read())))
            else:
                self.error_Response()
        elif path == "/multipart3":
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
            content_length = int(self.headers.get('Content-length', '-1'))
            if ctype == 'multipart/form-data':
                req = parse_multipart(req_body, self.headers)
                f = req['f']
                if not req['a'] == ['aa']:
                    self.error_Response()
                if not req['b'] == ['éàù@']:
                    self.error_Response()
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, str(len(f.file.read())))
            else:
                self.error_Response()
        elif path == "/multipart4":
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
            content_length = int(self.headers.get('Content-length', 0))
            if ctype == 'multipart/form-data':
                req = parse_multipart(req_body, self.headers)
                f = req['f']
                if not req['a'] == ['aa']:
                    self.error_Response()
                if not req['b'] == ['éàù@']:
                    self.error_Response()
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, f)
            else:
                self.error_Response()
        elif path == "/1M":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = req_body.read(content_length)
            self._respond(200, extra_headers, str(len(body)))
        elif path == "/large":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-Type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = req_body.read(content_length)
            extra_headers.append(('Content-Length', str(len(body))))
            self._respond(200, extra_headers, body)
        elif path == "/list":
            content_length = int(self.headers.get('Content-length', 0))
            body = req_body.read(content_length)
            extra_headers.append(('Content-Length', str(len(body))))
            self._respond(200, extra_headers, body)
        elif path == "/chunked":
            te = (self.headers.get("transfer-encoding") == "chunked")
            if te:
                body = req_body.read(29)
                extra_headers.append(('Content-Length', "29"))
                self._respond(200, extra_headers, body)
            else:
                self.error_Response()
        else:
            self.error_Response('Bad path')

    do_PUT = do_POST

    def do_DELETE(self):
        if self.path == "/delete":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, '')
        else:
            self.error_Response()

    def do_HEAD(self):
        if self.path == "/ok":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, '')
        else:
            self.error_Response()

    def error_Response(self, message=None):
        req = [
            ('HTTP method', self.command),
            ('path', self.path),
            ]
        if message:
            req.append(('message', message))

        body_parts = ['Bad request:\r\n']
        for k, v in req:
            body_parts.append(' %s: %s\r\n' % (k, v))
        body = ''.join(body_parts)
        self._respond(400, [('Content-type', 'text/plain'),
        ('Content-Length', str(len(body)))], body)


    def _respond(self, http_code, extra_headers, body):
        self.send_response(http_code)
        keys = []
        for k, v in extra_headers:
            self.send_header(k, v)
            keys.append(k)

        if body:
            body = to_bytestring(body)

        #if body and "Content-Length" not in keys:
        #    self.send_header("Content-Length", len(body))
        self.end_headers()

        if isinstance(body, string_types):
            body = str_to_bytes(body)

        self.wfile.write(body)
        sys.stderr.write("yokidoki")
        self.wfile.flush()


server_thread = None
def run_server_test():
    global server_thread
    if server_thread is not None:
        return


    server = HTTPServer((HOST, PORT), HTTPTestHandler)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()
