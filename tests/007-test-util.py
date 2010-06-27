# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import t
from restkit import util

def test_001():
    qs = {'a': "a"}
    t.eq(util.url_encode(qs), "a=a")
    qs = {'a': 'a', 'b': 'b'}
    t.eq(util.url_encode(qs), "a=a&b=b")
    qs = {'a': 1}
    t.eq(util.url_encode(qs), "a=1")
    qs = {'a': [1, 2]}
    t.eq(util.url_encode(qs), "a=1&a=2")
    qs = {'a': [1, 2], 'b': [3, 4]}
    t.eq(util.url_encode(qs), "a=1&a=2&b=3&b=4")
    qs = {'a': lambda : 1}
    t.eq(util.url_encode(qs), "a=1")
    
def test_002():
    t.eq(util.make_uri("http://localhost", "/"), "http://localhost/")
    t.eq(util.make_uri("http://localhost/"), "http://localhost/")
    t.eq(util.make_uri("http://localhost/", "/test/echo"), 
        "http://localhost/test/echo")
    t.eq(util.make_uri("http://localhost/", "/test/echo/"), 
        "http://localhost/test/echo/")
    t.eq(util.make_uri("http://localhost", "/test/echo/"),
        "http://localhost/test/echo/")
    t.eq(util.make_uri("http://localhost", "test/echo"), 
        "http://localhost/test/echo")
    t.eq(util.make_uri("http://localhost", "test/echo/"),
        "http://localhost/test/echo/")
    
    