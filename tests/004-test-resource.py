# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import t

from restkit.errors import RequestFailed, ResourceNotFound, \
Unauthorized, RequestError
from restkit.resource import Resource
from _server_test import HOST, PORT

def test_001():
    res = Resource("http://localhost")
    t.eq(res._make_uri("http://localhost", "/"), "http://localhost/")
    t.eq(res._make_uri("http://localhost/"), "http://localhost/")
    t.eq(res._make_uri("http://localhost/", "/test/echo"), 
        "http://localhost/test/echo")
    t.eq(res._make_uri("http://localhost/", "/test/echo/"), 
        "http://localhost/test/echo/")
    t.eq(res._make_uri("http://localhost", "/test/echo/"),
        "http://localhost/test/echo/")
    t.eq(res._make_uri("http://localhost", "test/echo"), 
        "http://localhost/test/echo")
    t.eq(res._make_uri("http://localhost", "test/echo/"),
        "http://localhost/test/echo/")

@t.resource_request()
def test_002(res):
    r = res.get()
    t.eq(r.status_int, 200)
    t.eq(r.body, "welcome")

@t.resource_request()
def test_003(res):
    r = res.get('/unicode')
    t.eq(r.body, "éàù@")

@t.resource_request()
def test_003(res):
    r = res.get('/éàù')
    t.eq(r.status_int, 200)
    t.eq(r.body, "ok")

@t.resource_request()
def test_003(res):
    r = res.get(u'/test')
    t.eq(r.status_int, 200)
    r = res.get(u'/éàù')
    t.eq(r.status_int, 200)

@t.resource_request()
def test_004(res):
    r = res.get('/json', headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    t.raises(RequestFailed, res.get, '/json', 
        headers={'Content-Type': 'text/plain'})
        
@t.resource_request()
def test_005(res):
    t.raises(ResourceNotFound, res.get, '/unknown')

@t.resource_request()
def test_006(res):
    r = res.get('/query', test='testing')
    t.eq(r.status_int, 200)
    r = res.get('/qint', test=1)
    t.eq(r.status_int, 200)

@t.resource_request()
def test_007(res):
    r = res.post(payload="test")
    t.eq(r.body, "test")

@t.resource_request()
def test_008(res):
    r = res.post('/bytestring', payload="éàù@")
    t.eq(r.body, "éàù@")

@t.resource_request()
def test_009(res):
    r = res.post('/unicode', payload=u"éàù@")
    t.eq(r.body, "éàù@")
    t.eq(r.unicode_body, u"éàù@")

@t.resource_request()
def test_010(res):
    r = res.post('/json', payload="test", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    t.raises(RequestFailed, res.post, '/json', payload='test',
            headers={'Content-Type': 'text/plain'})

@t.resource_request()
def test_011(res):
    r = res.post('/empty', payload="",
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    r = res.post('/empty', headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    
@t.resource_request()
def test_012(res):
    r = res.post('/query', test="testing")
    t.eq(r.status_int, 200)

@t.resource_request()
def test_013(res):
    r = res.post('/form', payload={ "a": "a", "b": "b" })
    t.eq(r.status_int, 200)
    
@t.resource_request()
def test_014(res):
    r = res.put(payload="test")
    t.eq(r.body, 'test')

@t.resource_request()
def test_015(res):
    r = res.head('/ok')
    t.eq(r.status_int, 200)

@t.resource_request()
def test_016(res):
    r = res.delete('/delete')    
    t.eq(r.status_int, 200)

@t.resource_request()
def test_017(res):
    content_length = len("test")
    import StringIO
    content = StringIO.StringIO("test")
    r = res.post('/json', payload=content,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': str(content_length)
            }) 
    t.eq(r.status_int, 200)

@t.resource_request()
def test_018(res):
    import StringIO
    content = StringIO.StringIO("test")
    t.raises(RequestFailed, res.post, '/json', payload=content,
            headers={'Content-Type': 'text/plain'})
            
def test_019():
    u = "http://test:test@%s:%s/auth" % (HOST, PORT)
    res = Resource(u)
    r = res.get()
    t.eq(r.status_int, 200)
    u = "http://test:test2@%s:%s/auth" % (HOST, PORT)
    res = Resource(u)
    t.raises(Unauthorized, res.get)
            
