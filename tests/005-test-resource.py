# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import t

from restkit.errors import RequestFailed, ResourceNotFound, \
Unauthorized
from restkit.resource import Resource
from _server_test import HOST, PORT

@t.resource_request()
def test_001(res):
    r = res.get()
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "welcome")

@t.resource_request()
def test_002(res):
    r = res.get('/unicode')
    t.eq(r.body_string(), "éàù@")

@t.resource_request()
def test_003(res):
    r = res.get('/éàù')
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "ok")

@t.resource_request()
def test_004(res):
    r = res.get(u'/test')
    t.eq(r.status_int, 200)
    r = res.get(u'/éàù')
    t.eq(r.status_int, 200)

@t.resource_request()
def test_005(res):
    r = res.get('/json', headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    t.raises(RequestFailed, res.get, '/json', 
        headers={'Content-Type': 'text/plain'})
        
@t.resource_request()
def test_006(res):
    t.raises(ResourceNotFound, res.get, '/unknown')

@t.resource_request()
def test_007(res):
    r = res.get('/query', test='testing')
    t.eq(r.status_int, 200)
    r = res.get('/qint', test=1)
    t.eq(r.status_int, 200)

@t.resource_request()
def test_008(res):
    r = res.post(payload="test")
    t.eq(r.body_string(), "test")

@t.resource_request()
def test_009(res):
    r = res.post('/bytestring', payload="éàù@")
    t.eq(r.body_string(), "éàù@")

@t.resource_request()
def test_010(res):
    r = res.post('/unicode', payload=u"éàù@")
    t.eq(r.body_string(), "éàù@")
    print "ok"
    r = res.post('/unicode', payload=u"éàù@")
    t.eq(r.body_string(charset="utf-8"), u"éàù@")

@t.resource_request()
def test_011(res):
    r = res.post('/json', payload="test", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    t.raises(RequestFailed, res.post, '/json', payload='test',
            headers={'Content-Type': 'text/plain'})

@t.resource_request()
def test_012(res):
    r = res.post('/empty', payload="",
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    r = res.post('/empty', headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    
@t.resource_request()
def test_013(res):
    r = res.post('/query', test="testing")
    t.eq(r.status_int, 200)

@t.resource_request()
def test_014(res):
    r = res.post('/form', payload={ "a": "a", "b": "b" })
    t.eq(r.status_int, 200)
    
@t.resource_request()
def test_015(res):
    r = res.put(payload="test")
    t.eq(r.body_string(), 'test')

@t.resource_request()
def test_016(res):
    r = res.head('/ok')
    t.eq(r.status_int, 200)

@t.resource_request()
def test_017(res):
    r = res.delete('/delete')    
    t.eq(r.status_int, 200)

@t.resource_request()
def test_018(res):
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
def test_019(res):
    import StringIO
    content = StringIO.StringIO("test")
    t.raises(RequestFailed, res.post, '/json', payload=content,
            headers={'Content-Type': 'text/plain'})
            
def test_020():
    u = "http://test:test@%s:%s/auth" % (HOST, PORT)
    res = Resource(u)
    r = res.get()
    t.eq(r.status_int, 200)
    u = "http://test:test2@%s:%s/auth" % (HOST, PORT)
    res = Resource(u)
    t.raises(Unauthorized, res.get)

@t.resource_request()
def test_021(res):
    r = res.post('/multivalueform', payload={ "a": ["a", "c"], "b": "b" })
    t.eq(r.status_int, 200)

@t.resource_request()
def test_022(res):
    import os
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    l = int(os.fstat(f.fileno())[6])
    b = {'a':'aa','b':['bb','éàù@'], 'f':f}
    h = {'content-type':"multipart/form-data"}
    r = res.post('/multipart2', payload=b, headers=h)
    t.eq(r.status_int, 200)
    t.eq(int(r.body_string()), l)

@t.resource_request()
def test_023(res):
    import os
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    l = int(os.fstat(f.fileno())[6])
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    r = res.post('/multipart3', payload=b, headers=h)
    t.eq(r.status_int, 200)
    t.eq(int(r.body_string()), l)

@t.resource_request()
def test_024(res):
    import os
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    content = f.read()
    f.seek(0)
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    r = res.post('/multipart4', payload=b, headers=h)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), content)

@t.resource_request()
def test_025(res):
    import StringIO
    content = 'éàù@'
    f = StringIO.StringIO('éàù@')
    f.name = 'test.txt'
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    r = res.post('/multipart4', payload=b, headers=h)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), content)