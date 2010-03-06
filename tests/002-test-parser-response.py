# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import t

@t.response("001.http")
def test_001(buf, p):
    headers = []
    buf2 = p.filter_headers(headers, buf)
    t.ne(buf2, False)
    t.eq(p.version, (1,1))
    t.eq(p.status, "301 Moved Permanently")
    t.eq(p.status_int, 301)
    t.eq(p.reason, "Moved Permanently")
    t.eq(sorted(p.headers), [
        ('Cache-Control', 'public, max-age=2592000'),
        ('Content-Length', '211'),
        ('Content-Type', 'text/html; charset=UTF-8'),
        ('Date', 'Sun, 26 Apr 2009 11:11:49 GMT'),
        ('Expires', 'Tue, 26 May 2009 11:11:49 GMT'),
        ('Location', 'http://www.google.com/'),
        ('Server', 'gws'),
    ])
    body, tr = p.filter_body(buf2)
    t.eq(p.content_len,len(body))
    t.eq(p.body_eof(), True)

@t.response("002.http")
def test_002(buf, p):
    headers = []
    buf2 = p.filter_headers(headers, buf)
    t.ne(buf2, False)
    t.eq(p.status_int, 200)
    t.eq(p.reason, 'OK')
    t.eq(sorted(p.headers), [
        ('Connection', 'close'),
        ('Content-Type', 'text/xml; charset=utf-8'),
        ('Date', 'Tue, 04 Aug 2009 07:59:32 GMT'),
        ('Server', 'Apache'),
        ('X-Powered-By', 'Servlet/2.5 JSP/2.1'),
        
    ])
    
    body, tr = p.filter_body(buf2)
    t.eq(p.body_eof(), True)

@t.response("003.http")
def test_003(buf, p):
    headers = []
    buf2 = p.filter_headers(headers, buf)
    t.ne(buf2, False)    
    t.eq(p.status_int, 404)
    body, tr = p.filter_body(buf2)
    t.eq(body,"")
    t.eq(p.body_eof(), True)
    
@t.response("004.http")
def test_004(buf, p):
    headers = []
    buf2 = p.filter_headers(headers, buf)
    t.ne(buf2, False)    
    t.eq(p.status_int, 301)
    t.eq(p.reason, "")
    
@t.response("005.http")
def test_005(buf, p):
    headers = []
    buf2 = p.filter_headers(headers, buf)
    t.ne(buf2, False)    
    t.eq(p.status_int, 200)
    t.eq(sorted(p.headers), [
        ('Content-Type', 'text/plain'),
        ('Transfer-Encoding', 'chunked')
    ])
    t.eq(p.is_chunked, True)
    t.eq(p._chunk_eof, False)
    t.ne(p.body_eof(), True)
    body = ""
    while not p.body_eof():
        chunk, buf2 = p.filter_body(buf2)
        print chunk
        if chunk:
            body += chunk
    t.eq(body, 
    "  This is the data in the first chunk  and this is the second one")
    t.eq(p.body_eof(), True)
    
@t.response("006.http")
def test_006(buf, p):
    headers = []
    buf2 = p.filter_headers(headers, buf)
    t.ne(buf2, False)    
    t.eq(p.status_int, 200)
    body, tr = p.filter_body(buf2)
    t.eq(body,"these headers are from http://news.ycombinator.com/")
    t.eq(p.body_eof(), True)
    
@t.response("007.http")
def test_007(buf, p):
    headers = []
    buf2 = p.filter_headers(headers, buf)
    t.ne(buf2, False)    
    t.eq(p.status_int, 200)
    body, tr = p.filter_body(buf2)
    t.eq(body,"hello world")
    t.eq(len(body), int(p.content_len))
    t.eq(p.body_eof(), True)