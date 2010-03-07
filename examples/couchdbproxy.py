# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import urlparse

from webob import Request
from restkit.pool import ConnectionPool
from restkit.ext.wsgi_proxy import HostProxy

pool = ConnectionPool(max_connections=10)
proxy = HostProxy("http://127.0.0.1:5984", pool=pool)


def application(environ, start_response):
    req = Request(environ)
    if 'RAW_URI' in req.environ: 
        # gunicorn so we use real path non encoded
        u = urlparse.urlparse(req.environ['RAW_URI'])
        req.environ['PATH_INFO'] = u.path

    # do smth like adding oauth headers ..
    resp = req.get_response(proxy)
    
    # rewrite response
    # do auth ...
    return resp(environ, start_response)