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

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
import os
import socket
import threading
import unittest
import urlparse
import urllib2

from restclient.http import Urllib2HTTPClient, CurlHTTPClient, \
HTTPLib2HTTPClient
from restclient.rest import Resource, RestClient, RequestFailed, \
ResourceNotFound


from _server_test import HOST, PORT

class ResourceTestCase(unittest.TestCase):

    def setUp(self):
        httpclient = Urllib2HTTPClient()
        self.url = 'http://%s:%s' % (HOST, PORT)
        self.res = Resource(self.url, httpclient)

    def tearDown(self):
        self.res = None

    def testGet(self):
        result = self.res.get()
        self.assert_(result == "welcome")

    def testGetWithContentType(self):
        result = self.res.get('/json', headers={'Content-Type': 'application/json'})
        self.assert_(self.res.status_code == 200)
        def bad_get():
            result = self.res.get('/json', headers={'Content-Type': 'text/plain'})
        self.assertRaises(RequestFailed, bad_get) 

    def testNotFound(self):
        def bad_get():
            result = self.res.get("/unknown")

        self.assertRaises(ResourceNotFound, bad_get)

    def testGetWithQuery(self):
        result = self.res.get('/query', test="testing")
        self.assert_(self.res.status_code == 200)


    def testSimplePost(self):
        result = self.res.post(payload="test")
        self.assert_(result=="test")

    def testPostWithContentType(self):
        result = self.res.post('/json', payload="test",
                headers={'Content-Type': 'application/json'})
        self.assert_(self.res.status_code == 200 )
        def bad_post():
            result = self.res.post('/json', payload="test",
                    headers={'Content-Type': 'text/plain'})
        self.assertRaises(RequestFailed, bad_post)

    def testEmptyPost(self):
        result = self.res.post('/empty', payload="",
                headers={'Content-Type': 'application/json'})
        self.assert_(self.res.status_code == 200 )
        result = self.res.post('/empty',headers={'Content-Type': 'application/json'})
        self.assert_(self.res.status_code == 200 )

    def testPostWithQuery(self):
        result = self.res.post('/query', test="testing")
        self.assert_(self.res.status_code == 200)

    def testSimplePut(self):
        result = self.res.put(payload="test")
        self.assert_(result=="test")

    def testPutWithContentType(self):
        result = self.res.put('/json', payload="test",
                headers={'Content-Type': 'application/json'})
        self.assert_(self.res.status_code == 200 )
        def bad_put():
            result = self.res.put('/json', payload="test",
                    headers={'Content-Type': 'text/plain'})
        self.assertRaises(RequestFailed, bad_put)

    def testEmptyPut(self):
        result = self.res.put('/empty', payload="",
                headers={'Content-Type': 'application/json'})
        self.assert_(self.res.status_code == 200 )
        result = self.res.put('/empty',headers={'Content-Type': 'application/json'})
        self.assert_(self.res.status_code == 200 )

    def testPuWithQuery(self):
        result = self.res.put('/query', test="testing")
        self.assert_(self.res.status_code == 200)

    def testHead(self):
        result = self.res.head('/ok')
        self.assert_(self.res.status_code == 200)

    def testDelete(self):
        result = self.res.delete('/delete')
        self.assert_(self.res.status_code == 200)


    def testAuth(self):
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, "%s/%s" % (self.url, "auth"),
                "test", "test")
        auth_handler = urllib2.HTTPBasicAuthHandler(password_mgr)

        httpclient = Urllib2HTTPClient(auth_handler)
        
        res = Resource(self.url, httpclient)
        
    
if __name__ == '__main__':
    from _server_test import run_server_test
    run_server_test() 
    unittest.main()
