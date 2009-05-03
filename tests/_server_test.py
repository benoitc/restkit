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
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
import os
import socket
import threading
import unittest
import urlparse
import urllib
from restclient.utils import to_bytestring

HOST = socket.getfqdn('127.0.0.1')
PORT = (os.getpid() % 31000) + 1024

class HTTPTestHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.auth = 'Basic ' + base64.encodestring('test:test')[:-1]
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        
    def do_GET(self):
        self.parsed_uri = urlparse.urlparse(urllib.unquote(self.path))
        self.query = {}
        for k, v in cgi.parse_qsl(self.parsed_uri[4]):
            self.query[k] = v.decode('utf-8')
        path = self.parsed_uri[2]

        if path == "/":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "welcome")

        elif path == "/unicode":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, u"éàù@")

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
                auth = self.headers['Authorization'][len('Basic')+1:]
                auth = base64.b64decode(auth).split(':')
                if auth[0] == "test" and auth[1] == "test":
                    self._respond(200, extra_headers, "ok")
                else:
                    self._respond(403, extra_headers, "niet!")
        else:
            self._respond(404, 
                [('Content-type', 'text/plain')], "Not Found" )


    def do_POST(self):
        self.parsed_uri = urlparse.urlparse(self.path)
        self.query = {}
        for k, v in cgi.parse_qsl(self.parsed_uri[4]):
            self.query[k] = v.decode('utf-8')
        path = self.parsed_uri[2]
        extra_headers = []
        if path == "/":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = self.rfile.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/bytestring":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = self.rfile.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/unicode":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = self.rfile.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/json":
            content_type = self.headers.get('content-type', 'text/plain')
            if content_type != "application/json":
                self.error_Response("bad type")
            else:
                extra_headers.append(('Content-type', content_type))
                content_length = int(self.headers.get('Content-length', 0))
                body = self.rfile.read(content_length)
                self._respond(200, extra_headers, body)
        elif path == "/empty":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = self.rfile.read(content_length)
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
            body = self.rfile.read(content_length)
            form = urlparse.parse_qs(body)
            if form['a'] == ["a"] and form["b"] == ["b"]:
                self._respond(200, extra_headers, "ok")
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
        self._respond(400, [('Content-type', 'text/plain')], body)


    def _respond(self, http_code, extra_headers, body):
        self.send_response(http_code)
        for k, v in extra_headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(to_bytestring(body))
        self.wfile.close()

    def finish(self):
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()


server_thread = None
def run_server_test():
    global server_thread

    try:
        server = HTTPServer((HOST, PORT), HTTPTestHandler)

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()
    except:
        pass

if __name__ == '__main__':
    pass
