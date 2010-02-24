# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import cgi
import imghdr
import os
import socket
import threading
import Queue
import urlparse
import sys
import tempfile
import time

import t
from restkit.filters import BasicAuth

from _server_test import HOST, PORT, run_server_test
run_server_test()


LONG_BODY_PART = """This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client..."""

@t.client_request("/")
def test_001(u, c):
    r = c.request(u)
    t.eq(r.body, "welcome")
    c.maybe_close()
    
@t.client_request("/unicode")
def test_002(u, c):
    r = c.request(u)
    t.eq(r.unicode_body, u"éàù@")
    c.maybe_close()
    
@t.client_request("/éàù")
def test_003(u, c):
    r = c.request(u)
    t.eq(r.body, "ok")
    t.eq(r.status_int, 200)
    c.maybe_close()

@t.client_request("/json")
def test_004(u, c):
    r = c.request(u, headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    c.maybe_close()
    r = c.request(u, headers={'Content-Type': 'text/plain'})
    t.eq(r.status_int, 400)
    c.maybe_close()

@t.client_request('/unkown')
def test_005(u, c):
    r = c.request(u, headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 404)
    c.maybe_close()
    
@t.client_request('/query?test=testing')
def test_006(u, c):
    r = c.request(u)
    t.eq(r.status_int, 200)
    t.eq(r.body, "ok")
    c.maybe_close()

@t.client_request('http://e-engura.com/images/logo.gif')
def test_007(u, c):
    r = c.request(u)
    print r.status
    t.eq(r.status_int, 200)
    fd, fname = tempfile.mkstemp(suffix='.gif')
    f = os.fdopen(fd, "wb")
    f.write(r.body)
    f.close()
    t.eq(imghdr.what(fname), 'gif')
    c.maybe_close()

@t.client_request('http://e-engura.com/images/logo.gif')
def test_008(u, c):
    r = c.request(u)
    t.eq(r.status_int, 200)
    fd, fname = tempfile.mkstemp(suffix='.gif')
    f = os.fdopen(fd, "wb")
    for block in r.body_file:
        f.write(block)
    f.close()
    t.eq(imghdr.what(fname), 'gif')
    c.maybe_close()

@t.client_request('/redirect')
def test_009(u, c):
    c.follow_redirect = True
    r = c.request(u)
    
    
    complete_url = "%s/complete_redirect" % u.rsplit("/", 1)[0]
    t.eq(r.status_int, 200)
    t.eq(r.body, "ok")
    t.eq(r.final_url, complete_url)
    c.maybe_close()

@t.client_request('/')
def test_010(u, c):
    r = c.request(u, 'POST', body="test")
    t.eq(r.body, "test")
    c.maybe_close()

@t.client_request('/bytestring')
def test_011(u, c):
    r = c.request(u, 'POST', body="éàù@")
    t.eq(r.body, "éàù@")
    c.maybe_close()

@t.client_request('/unicode')
def test_012(u, c):
    r = c.request(u, 'POST', body=u"éàù@")
    t.eq(r.body, "éàù@")
    c.maybe_close()       

@t.client_request('/json')
def test_013(u, c):
    r = c.request(u, 'POST', body="test", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    c.maybe_close()
    r = c.request(u, 'POST', body="test", 
            headers={'Content-Type': 'text/plain'})
    t.eq(r.status_int, 400)
    c.maybe_close()
    
@t.client_request('/empty')
def test_014(u, c):
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    c.maybe_close()

@t.client_request('/query?test=testing')
def test_015(u, c):
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    c.maybe_close()

@t.client_request('/1M')
def test_016(u, c):
    fn = os.path.join(os.path.dirname(__file__), "1M")
    with open(fn, "rb") as f:
        l = int(os.fstat(f.fileno())[6])
        r = c.request(u, 'POST', body=f)
        t.eq(r.status_int, 200)
        t.eq(int(r.body), l)
    c.maybe_close()

@t.client_request('/large')
def test_017(u, c):
    r = c.request(u, 'POST', body=LONG_BODY_PART)
    t.eq(r.status_int, 200)
    t.eq(int(r['content-length']), len(LONG_BODY_PART))
    t.eq(r.body, LONG_BODY_PART)
    c.maybe_close()   


def test_0018():
    for i in range(10):
        t.client_request('/large', test_017)
        
@t.client_request('/')
def test_019(u, c):
    r = c.request(u, 'PUT', body="test")
    t.eq(r.body, "test")
    c.maybe_close()
    
@t.client_request('/auth')
def test_020(u, c):
    auth_filter = BasicAuth("test", "test")
    c.add_filter(auth_filter)
    r = c.request(u)
    t.eq(r.status_int, 200)
    c.maybe_close()
    
    c.remove_filter(auth_filter)
    t.eq(len(c.filters), 0)
    auth_filter1 = BasicAuth("test", "test2")
    c.add_filter(auth_filter1)
    r = c.request(u)
    t.eq(r.status_int, 403)

