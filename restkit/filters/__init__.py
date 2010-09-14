# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

"""
filters - Http filters

Http filters are object used before sending the request to the server
and after. The `HttpClient` instance is passed as argument.

An object with a method `on_request` is called just before the request. 
An object with a method `on_response` is called after fetching response headers.

ex::

    class MyFilter(object):
        
        def on_request(self, http_client):
            "do something with/to http_client instance"

        def on_response(self, http_client):
            "do something on http_client and get response infos"
            
            
"""

from restkit.filters.basicauth import BasicAuth
from restkit.filters.oauth2 import OAuthFilter
from restkit.filters.simpleproxy import SimpleProxy

class Filters(object):
    
    def __init__(self, filters=None):
        self.filters = filters or []
        
    def add(self, obj):
        if not hasattr(obj, "on_request") and not hasattr(obj, "on_response"):
            raise TypeError("%s is not a filter object." % obj.__class__.__name__)
            
        self.filters.append(obj)
        
    def remove(self, obj):
        for i, f in enumerate(self.filters):
            if obj == f: del self.filters[i]
            
    def apply(self, kind, *args):
        for f in self.filters:
            try:
                func = getattr(f, kind)
            except AttributeError:
                continue
            func(*args)
