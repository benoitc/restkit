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

from restkit.errors import ResourceNotFound, Unauthorized, \
RequestFailed, ResourceGone
from restkit.client import Client
from restkit.filters import BasicAuth
from restkit import util
from restkit.wrappers import Response

class Resource(object):
    """A class that can be instantiated for access to a RESTful resource, 
    including authentication. 
    """
    
    charset = 'utf-8'
    encode_keys = True
    safe = "/:"
    basic_auth_url = True
    response_class = Response
    
    def __init__(self, uri, **client_opts):
        """Constructor for a `Resource` object.

        Resource represent an HTTP resource.

        :param uri: str, full uri to the server.
        :param client_opts: `restkit.client.Client` Options
        """
        client_opts = client_opts or {} 

        self.initial = dict(
            uri = uri,
            client_opts = client_opts.copy()
        )

        # set default response_class
        if self.response_class is not None and \
                not 'response_class' in client_opts:
            client_opts['response_class'] = self.response_class 

        self.filters = client_opts.get('filters') or []
        self.uri = uri
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
                self.uri = urlparse.urlunparse((u.scheme, u.netloc.split("@")[-1],
                    u.path, u.params, u.query, u.fragment))

        self.client_opts = client_opts
        self.client = Client(**self.client_opts)
        
    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.uri)
        
    def clone(self):
        """if you want to add a path to resource uri, you can do:

        .. code-block:: python

            resr2 = res.clone()
        
        """
        obj = self.__class__(self.initial['uri'], 
                **self.initial['client_opts'])
        return obj
   
    def __call__(self, path):
        """if you want to add a path to resource uri, you can do:
        
        .. code-block:: python

            Resource("/path").get()
        """

        uri = self.initial['uri']

        new_uri = util.make_uri(uri, path, charset=self.charset, 
                        safe=self.safe, encode_keys=self.encode_keys)
        
        obj = type(self)(new_uri, **self.initial['client_opts'])
        return obj
         
    def get(self, path=None, headers=None, params_dict=None, **params):
        """ HTTP GET         
        
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request.
        """
        return self.request("GET", path=path, headers=headers,
                params_dict=params_dict, **params)

    def head(self, path=None, headers=None, params_dict=None, **params):
        """ HTTP HEAD

        see GET for params description.
        """
        return self.request("HEAD", path=path, headers=headers,
                params_dict=params_dict, **params)

    def delete(self, path=None, headers=None, params_dict=None, **params):
        """ HTTP DELETE

        see GET for params description.
        """
        return self.request("DELETE", path=path, headers=headers,
                params_dict=params_dict, **params)

    def post(self, path=None, payload=None, headers=None,
            params_dict=None, **params):
        """ HTTP POST

        :param payload: string passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request
        """

        return self.request("POST", path=path, payload=payload, 
                        headers=headers, params_dict=params_dict, **params)

    def put(self, path=None, payload=None, headers=None,
            params_dict=None, **params):
        """ HTTP PUT

        see POST for params description.
        """
        return self.request("PUT", path=path, payload=payload,
                        headers=headers, params_dict=params_dict, **params)
                        
    def make_params(self, params):
        return params or {}
        
    def make_headers(self, headers):
        return headers or []
        
    def unauthorized(self, response):
        return True

    def request(self, method, path=None, payload=None, headers=None, 
        params_dict=None, **params):
        """ HTTP request

        This method may be the only one you want to override when
        subclassing `restkit.rest.Resource`.
        
        :param payload: string or File object passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :params_dict: Options parameters added to the request as a dict
        :param params: Optionnal parameterss added to the request
        """
        
        params = params or {}
        params.update(params_dict or {})

        while True:
            uri = util.make_uri(self.uri, path, charset=self.charset, 
                        safe=self.safe, encode_keys=self.encode_keys,
                        **self.make_params(params))
        
            # make request
            
            resp = self.client.request(uri, method=method, body=payload, 
                        headers=self.make_headers(headers))
            
            if resp is None:
                # race condition
                raise ValueError("Unkown error: response object is None")

            if resp.status_int >= 400:
                if resp.status_int == 404:
                    raise ResourceNotFound(resp.body_string(), 
                                response=resp)
                elif resp.status_int in (401, 403):
                    if self.unauthorized(resp):
                        raise Unauthorized(resp.body_string(), 
                                http_code=resp.status_int, 
                                response=resp)
                elif resp.status_int == 410:
                    raise ResourceGone(resp.body_string(), response=resp)
                else:
                    raise RequestFailed(resp.body_string(), 
                                http_code=resp.status_int,
                                response=resp)
            else:
                break

        return resp

    def update_uri(self, path):
        """
        to set a new uri absolute path
        """
        self.uri = util.make_uri(self.uri, path, charset=self.charset, 
                        safe=self.safe, encode_keys=self.encode_keys)
        self.initial['uri'] =  util.make_uri(self.initial['uri'], path, 
                                    charset=self.charset, 
                                    safe=self.safe, 
                                    encode_keys=self.encode_keys)
