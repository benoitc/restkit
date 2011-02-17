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
    t.eq(r.body_string(), "welcome")
    
@t.client_request("/unicode")
def test_002(u, c):
    r = c.request(u)
    t.eq(r.body_string(charset="utf-8"), u"éàù@")
    
@t.client_request("/éàù")
def test_003(u, c):
    r = c.request(u)
    t.eq(r.body_string(), "ok")
    t.eq(r.status_int, 200)

@t.client_request("/json")
def test_004(u, c):
    r = c.request(u, headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    r = c.request(u, headers={'Content-Type': 'text/plain'})
    t.eq(r.status_int, 400)


@t.client_request('/unkown')
def test_005(u, c):
    r = c.request(u, headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 404)
    
@t.client_request('/query?test=testing')
def test_006(u, c):
    r = c.request(u)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "ok")
    

@t.client_request('http://e-engura.com/images/logo.gif')
def test_007(u, c):
    r = c.request(u)
    print r.status
    t.eq(r.status_int, 200)
    fd, fname = tempfile.mkstemp(suffix='.gif')
    f = os.fdopen(fd, "wb")
    f.write(r.body_string())
    f.close()
    t.eq(imghdr.what(fname), 'gif')
    

@t.client_request('http://e-engura.com/images/logo.gif')
def test_008(u, c):
    r = c.request(u)
    t.eq(r.status_int, 200)
    fd, fname = tempfile.mkstemp(suffix='.gif')
    f = os.fdopen(fd, "wb")
    with r.body_stream() as body:
        for block in body:
            f.write(block)
    f.close()
    t.eq(imghdr.what(fname), 'gif')
    

@t.client_request('/redirect')
def test_009(u, c):
    c.follow_redirect = True
    r = c.request(u)

    complete_url = "%s/complete_redirect" % u.rsplit("/", 1)[0]
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "ok")
    t.eq(r.final_url, complete_url)
    

@t.client_request('/')
def test_010(u, c):
    r = c.request(u, 'POST', body="test")
    t.eq(r.body_string(), "test")
    

@t.client_request('/bytestring')
def test_011(u, c):
    r = c.request(u, 'POST', body="éàù@")
    t.eq(r.body_string(), "éàù@")
    

@t.client_request('/unicode')
def test_012(u, c):
    r = c.request(u, 'POST', body=u"éàù@")
    t.eq(r.body_string(), "éàù@")
           

@t.client_request('/json')
def test_013(u, c):
    r = c.request(u, 'POST', body="test", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    
    r = c.request(u, 'POST', body="test", 
            headers={'Content-Type': 'text/plain'})
    t.eq(r.status_int, 400)
    
    
@t.client_request('/empty')
def test_014(u, c):
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    

@t.client_request('/query?test=testing')
def test_015(u, c):
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    

@t.client_request('/1M')
def test_016(u, c):
    fn = os.path.join(os.path.dirname(__file__), "1M")
    with open(fn, "rb") as f:
        l = int(os.fstat(f.fileno())[6])
        r = c.request(u, 'POST', body=f)
        t.eq(r.status_int, 200)
        t.eq(int(r.body_string()), l)
    

@t.client_request('/large')
def test_017(u, c):
    r = c.request(u, 'POST', body=LONG_BODY_PART)
    t.eq(r.status_int, 200)
    t.eq(int(r['content-length']), len(LONG_BODY_PART))
    t.eq(r.body_string(), LONG_BODY_PART)
       


def test_0018():
    for i in range(10):
        t.client_request('/large')(test_017)
        
@t.client_request('/')
def test_019(u, c):
    r = c.request(u, 'PUT', body="test")
    t.eq(r.body_string(), "test")
    
    
@t.client_request('/auth')
def test_020(u, c):
    c.filters = [BasicAuth("test", "test")]
    c.load_filters()
    r = c.request(u)
    t.eq(r.status_int, 200)
    
    c.filters = [BasicAuth("test", "test2")]
    c.load_filters()
    r = c.request(u)
    t.eq(r.status_int, 403)
   

@t.client_request('/list')
def test_021(u, c):
    lines = ["line 1\n", " line2\n"]
    r = c.request(u, 'POST', body=lines, 
            headers=[("Content-Length", "14")])
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), 'line 1\n line2\n')
     
@t.client_request('/chunked')
def test_022(u, c):
    lines = ["line 1\n", " line2\n"]
    r = c.request(u, 'POST', body=lines, 
            headers=[("Transfer-Encoding", "chunked")])
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), '7\r\nline 1\n\r\n7\r\n line2\n\r\n0\r\n\r\n')
    


