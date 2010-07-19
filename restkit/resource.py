# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


"""
restkit.resource
~~~~~~~~~~~~~~~~

This module provide a common interface for all HTTP request. 
"""
from copy import copy
import urlparse

from restkit.errors import ResourceNotFound, Unauthorized, RequestFailed,\
ParserError, RequestError
from restkit.client import HttpConnection
from restkit.filters import BasicAuth
from restkit import util
from restkit.pool.simple import SimplePool

class Resource(object):
    """A class that can be instantiated for access to a RESTful resource, 
    including authentication. 
    """
    
    charset = 'utf-8'
    encode_keys = True
    safe = "/:"
    pool_class = SimplePool
    keepalive = True
    basic_auth_url = True
    
    def __init__(self, uri, headers=None, **client_opts):
        """Constructor for a `Resource` object.

        Resource represent an HTTP resource.

        :param uri: str, full uri to the server.
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param client_opts: `restkit.client.HttpConnection` Options
        """

        pool_instance = client_opts.get('pool_instance')
        keepalive = client_opts.get("keepalive") or 10
        if not pool_instance and self.keepalive:
            pool = self.pool_class(keepalive=keepalive)
            client_opts['pool_instance'] = pool
            
        self.filters = client_opts.get('filters') or []
        if self.basic_auth_url:
            # detect credentials from url
            u = urlparse.urlparse(uri)
            if u.username:
                password = u.password or ""
                
                # add filters
                filters = copy(self.filters)                
                filters.append(BasicAuth(u.username, password))
                client_opts['filters'] = filters
                
                # update uri
                uri = urlparse.urlunparse((u.scheme, u.netloc.split("@")[-1],
                    u.path, u.params, u.query, u.fragment))
                
        self.uri = uri
        self._headers = headers or {}
        self.client_opts = client_opts
        self._body_parts = []

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.uri)
        
    def _set_default_attrs(self, obj):
        for attr_name in ('charset', 'encode_keys', 'pool_class',
                'keepalive', 'basic_auth_url'):
            setattr(obj, attr_name, getattr(self, attr_name))
        return obj
        
    def clone(self):
        """if you want to add a path to resource uri, you can do:

        .. code-block:: python

            resr2 = res.clone()
        
        """
        client_opts = self.client_opts.copy()
        client_opts["filters"] = self.filters
        obj = self.__class__(self.uri, headers=self._headers, 
                        **client_opts)
        return self._set_default_attrs(obj)
   
    def __call__(self, path):
        """if you want to add a path to resource uri, you can do:
        
        .. code-block:: python

            Resource("/path").get()
        """

        client_opts = self.client_opts.copy()
        client_opts["filters"] = self.filters
        
        new_uri = util.make_uri(self.uri, path, charset=self.charset, 
                        safe=self.safe, encode_keys=self.encode_keys)
                        
        obj = type(self)(new_uri, headers=self._headers, **client_opts)
        return self._set_default_attrs(obj)
        
    def close(self):
        """ Close all the connections related to the resource """
        pool = self.client_opts.get('pool_instance')
        if not pool: 
            return
        
        parsed_url = urlparse.urlparse(self.uri)
        pool.clear_host(util.parse_netloc(parsed_url))
 
    def get(self, path=None, headers=None, **params):
        """ HTTP GET         
        
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request.
        """
        return self.request("GET", path=path, headers=headers, **params)

    def head(self, path=None, headers=None, **params):
        """ HTTP HEAD

        see GET for params description.
        """
        return self.request("HEAD", path=path, headers=headers, **params)

    def delete(self, path=None, headers=None, **params):
        """ HTTP DELETE

        see GET for params description.
        """
        return self.request("DELETE", path=path, headers=headers, **params)

    def post(self, path=None, payload=None, headers=None, **params):
        """ HTTP POST

        :param payload: string passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request
        """

        return self.request("POST", path=path, payload=payload, 
                        headers=headers, **params)

    def put(self, path=None, payload=None, headers=None, **params):
        """ HTTP PUT

        see POST for params description.
        """
        return self.request("PUT", path=path, payload=payload,
                        headers=headers, **params)
                        
    def do_request(self, url, method='GET', payload=None, headers=None):
        http_client = HttpConnection(**self.client_opts)
        return http_client.request(url, method=method, body=payload, 
                            headers=headers)

    def request(self, method, path=None, payload=None, headers=None, 
        **params):
        """ HTTP request

        This method may be the only one you want to override when
        subclassing `restkit.rest.Resource`.
        
        :param payload: string or File object passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request
        """
        
        headers = headers or []
        uri = util.make_uri(self.uri, path, charset=self.charset, 
                        safe=self.safe, encode_keys=self.encode_keys,
                        **params)
        
        resp = self.do_request(uri, method=method, payload=payload, 
                                headers=headers)
            
        if resp is None:
            # race condition
            raise ValueError("Unkown error: response object is None")

        if resp.status_int >= 400:
            if resp.status_int == 404:
                raise ResourceNotFound(resp.body_string(), response=resp)
            elif resp.status_int in (401, 403):
                raise Unauthorized(resp.body_string(), 
                                   http_code=resp.status_int, response=resp)
            else:
                raise RequestFailed(resp.body_string(), 
                                    http_code=resp.status_int, response=resp)

        return resp

    def update_uri(self, path):
        """
        to set a new uri absolute path
        """
        self.uri = util.make_uri(self.uri, path, charset=self.charset, 
                        safe=self.safe, encode_keys=self.encode_keys)