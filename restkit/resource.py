# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


"""
restkit.resource
~~~~~~~~~~~~~~~~

This module provide a common interface for all HTTP request. 
"""

import cgi
import mimetypes
import uuid
import urlparse

from restkit.errors import ResourceNotFound, Unauthorized, RequestFailed,\
ParserError, RequestError
from restkit.forms import MultipartForm, multipart_form_encode, form_encode
from restkit.client import HttpConnection
from restkit.filters import BasicAuth
from restkit import util
from restkit import pool

class Resource(object):
    """A class that can be instantiated for access to a RESTful resource, 
    including authentication. 
    """
    
    charset = 'utf-8'
    encode_keys = True
    safe = "/:"
    pool_class = pool.ConnectionPool
    keepalive = True
    max_connections = 4
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
        if not pool_instance and self.keepalive:
            pool = self.pool_class(max_connections=self.max_connections)
            client_opts['pool_instance'] = pool
            
        if self.basic_auth_url:
            # detect credentials from url
            u = urlparse.urlparse(uri)
            if u.username:
                password = u.password or ""
                
                # add filters
                filters = client_opts.get('filters', [])
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
        
    def add_filter(self, f):
        """ add an htt filter """
        filters = self.client_opts.get('filters', [])
        filters.append(f)
        self.client_opts['filters'] = filters

    add_authorization = util.deprecated_property(
        add_filter, 'add_authorization', 'use add_filter() instead',
        warning=False)
        
    def remmove_filter(self, f):
        """ remove an http filter """
        filters = self.client_opts.get('filters', [])
        for i, f1 in enumerate(filters):
            if f == f1: del filters[i]
        self.client_opts['filters'] = filters
    
    def clone(self):
        """if you want to add a path to resource uri, you can do:

        .. code-block:: python

            resr2 = res.clone()
        
        """
        obj = self.__class__(self.uri, headers=self._headers, 
                        **self.client_opts)
             
        for attr in ('charset', 'encode_keys', 'safe', 'pool_class',
                'keepalive', 'max_connections', 'basic_auth_url'):
            setattr(obj, attr, getattr(self, attr))           
        return obj
   
    def __call__(self, path):
        """if you want to add a path to resource uri, you can do:
        
        .. code-block:: python

            Resource("/path").get()
        """

        new_uri = self._make_uri(self.uri, path)
        obj = type(self)(new_uri, headers=self._headers, **self.client_opts)
        for attr in ('charset', 'encode_keys', 'safe', 'pool_class',
                'keepalive', 'max_connections', 'basic_auth_url'):
            setattr(obj, attr, getattr(self, attr))
        return obj
 
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
        
        headers = headers or {}
        headers.update(self._headers.copy())

        
        self._body_parts = []
        if payload is not None:
            if isinstance(payload, dict):
                ctype = headers.get('Content-Type')
                if ctype is not None and \
                        ctype.startswith("multipart/form-data"):
                    type_, opts = cgi.parse_header(ctype)
                    boundary = opts.get('boundary', uuid.uuid4().hex)
                    payload, headers = multipart_form_encode(payload, 
                                                headers, boundary)
                else:
                    ctype = "application/x-www-form-urlencoded; charset=utf-8"
                    headers['Content-Type'] = ctype
                    payload = form_encode(payload)
                    headers['Content-Length'] = len(payload)
            elif isinstance(payload, MultipartForm):
                ctype = "multipart/form-data; boundary=%s" % payload.boundary
                headers['Content-Type'] = ctype
                headers['Content-Length'] = str(payload.get_size())

            if 'Content-Type' not in headers:
                ctype = 'application/octet-stream'
                if hasattr(payload, 'name'):
                    ctype = mimetypes.guess_type(payload.name)[0]

                headers['Content-Type'] = ctype
                
    
        uri = self._make_uri(self.uri, path, **params)
        
        try:
            resp = self.do_request(uri, method=method, payload=payload, 
                                headers=headers)
        except ParserError:
            raise
        except Exception, e:
            raise RequestError(e)
            
        if resp is None:
            # race condition
            raise RequestError("unkown error")

        if resp.status_int >= 400:
            if resp.status_int == 404:
                raise ResourceNotFound(resp.body, http_code=404, response=resp)
            elif resp.status_int in (401, 403):
                raise Unauthorized(resp.body, http_code=resp.status_int,
                        response=resp)
            else:
                raise RequestFailed(resp.body, http_code=resp.status_int,
                    response=resp)

        return resp

    def update_uri(self, path):
        """
        to set a new uri absolute path
        """
        self.uri = self._make_uri(self.uri, path)

    def _make_uri(self, base, *path, **query):
        """Assemble a uri based on a base, any number of path segments, 
        and query string parameters.

        """
        base_trailing_slash = False
        if base and base.endswith("/"):
            base_trailing_slash = True
            base = base[:-1]
        retval = [base]

        # build the path
        _path = []
        trailing_slash = False       
        for s in path:
            if s is not None and isinstance(s, basestring):
                if len(s) > 1 and s.endswith('/'):
                    trailing_slash = True
                else:
                    trailing_slash = False
                _path.append(util.url_quote(s.strip('/'), self.charset, self.safe))
                       
        path_str =""
        if _path:
            path_str = "/".join([''] + _path)
            if trailing_slash:
                path_str = path_str + "/" 
        elif base_trailing_slash:
            path_str = path_str + "/" 
            
        if path_str:
            retval.append(path_str)

        params_str = util.url_encode(query, self.charset, self.encode_keys)
        if params_str:
            retval.extend(['?', params_str])

        return ''.join(retval)