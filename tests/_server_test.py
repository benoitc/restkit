# -*- coding: utf-8 -
# Copyright (c) 2008, Benoît Chesneau <benoitc@e-engura.com>.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing per
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
import os
import socket
import threading
import unittest
import urlparse

HOST = socket.getfqdn('127.0.0.1')
PORT = (os.getpid() % 31000) + 1024

class HTTPTestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.parsed_uri = urlparse.urlparse(self.path)
        self.query = {}
        for k, v in cgi.parse_qsl(self.parsed_uri[4]):
            self.query[k] = v.decode('utf-8')
        path = self.parsed_uri[2]
        

        if path == "/":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "welcome")
        elif path == "/json":
            content_type = self.headers.get('content-type', 'text/plain')
            if content_type != "application/json":
                self.error_Response("bad type")
            else:
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")
                
        elif path == "/query":
            test = self.query.get("test", False)
            if test and test == "testing":
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
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
        self.wfile.write(body)
        self.wfile.close()

    def finish(self):
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()

def run_server_test():
    try:
        server = HTTPServer((HOST, PORT), HTTPTestHandler)

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()
    except:
        pass

