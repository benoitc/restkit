# -*- coding: utf-8 -*-
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import t
from _server_test import HOST, PORT
from restkit.contrib import wsgi_proxy

root_uri = "http://%s:%s" % (HOST, PORT)

def with_webob(func):
    def wrapper(*args, **kwargs):
        from webob import Request
        req = Request.blank('/')
        req.environ['SERVER_NAME'] = '%s:%s' % (HOST, PORT)
        return func(req)
    wrapper.func_name = func.func_name
    return wrapper

@with_webob
def test_001(req):
    req.path_info = '/query'
    proxy = wsgi_proxy.Proxy()
    resp = req.get_response(proxy)
    body = resp.body
    assert 'path: /query' in body, str(resp)

@with_webob
def test_002(req):
    req.path_info = '/json'
    req.environ['CONTENT_TYPE'] = 'application/json'
    req.method = 'POST'
    req.body = 'test post'
    proxy = wsgi_proxy.Proxy(allowed_methods=['POST'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.content_length == 9, str(resp)

    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    assert resp.status.startswith('403'), resp.status

@with_webob
def test_003(req):
    req.path_info = '/json'
    req.environ['CONTENT_TYPE'] = 'application/json'
    req.method = 'PUT'
    req.body = 'test post'
    proxy = wsgi_proxy.Proxy(allowed_methods=['PUT'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.content_length == 9, str(resp)

    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    assert resp.status.startswith('403'), resp.status

@with_webob
def test_004(req):
    req.path_info = '/ok'
    req.method = 'HEAD'
    proxy = wsgi_proxy.Proxy(allowed_methods=['HEAD'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.content_type == 'text/plain', str(resp)

@with_webob
def test_005(req):
    req.path_info = '/delete'
    req.method = 'DELETE'
    proxy = wsgi_proxy.Proxy(allowed_methods=['DELETE'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.content_type == 'text/plain', str(resp)

    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    assert resp.status.startswith('403'), resp.status

@with_webob
def test_006(req):
    req.path_info = '/redirect'
    req.method = 'GET'
    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.location == '%s/complete_redirect' % root_uri, str(resp)

@with_webob
def test_007(req):
    req.path_info = '/redirect_to_url'
    req.method = 'GET'
    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    body = resp.body

    print resp.location
    assert resp.location == '%s/complete_redirect' % root_uri, str(resp)

@with_webob
def test_008(req):
    req.path_info = '/redirect_to_url'
    req.script_name = '/name'
    req.method = 'GET'
    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'], strip_script_name=True)
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.location == '%s/name/complete_redirect' % root_uri, str(resp)



