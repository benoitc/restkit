# -*- coding: utf-8 -
#
# Copyright (c) 2008, 2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
restkit.rest
~~~~~~~~~~~~~~~

This module provide a common interface for all HTTP equest. 

    >>> from restkit import Resource
    >>> res = Resource('http://friendpaste.com')
    >>> res.get('/5rOqE9XTz7lccLgZoQS4IP',headers={'Accept': 'application/json'}).body
    u'{"snippet": "hi!", "title": "", "id": "5rOqE9XTz7lccLgZoQS4IP", "language": "text", "revision": "386233396230"}'
    >>> res.status
    200
"""

import cgi
import mimetypes
import uuid
import os
import types

from restkit.errors import ResourceNotFound, Unauthorized, RequestError, RequestFailed
from restkit.forms import MultipartForm, multipart_form_encode, form_encode
from restkit.httpc import HttpClient
from restkit.utils import to_bytestring, url_encode, url_quote


class Resource(object):
    """A class that can be instantiated for access to a RESTful resource, 
    including authentication. 
    """
    
    charset = 'utf-8'
    encode_keys = True
    safe = "/:"
    
    def __init__(self, uri, transport=None, headers=None, **client_opts):
        """Constructor for a `Resource` object.

        Resource represent an HTTP resource.

        :param uri: str, full uri to the server.
        :param transport: any http instance of object based on 
                `restkit.http.HTTPClient`. By default it will use 
                a client based on `pycurl <http://pycurl.sourceforge.net/>`_ if 
                installed or urllib2. You could also use 
                `restkit.http.HTTPLib2HTTPClient`,a client based on 
                `Httplib2 <http://code.google.com/p/httplib2/>`_ or make your
                own depending of the option you need to access to the serve
                (authentification, proxy, ....).
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param client_opts: `HttpClient` Options
        """

        if transport is None:
            self.transport = HttpClient(**client_opts)
        else:
            self.transport = transport
            
        self.uri = uri
        self._headers = headers or {}
        self.client_opts = client_opts
        self._body_parts = []

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.uri)
        
    def add_authorization(self, obj_auth):
        self.transport.add_authorization(obj_auth)

    def clone(self):
        """if you want to add a path to resource uri, you can do:

        .. code-block:: python

            resr2 = res.clone()
        
        """
        obj = self.__class__(self.uri, transport=self.transport, 
                    headers=self._headers, **self.client_opts)
        return obj
   
    def __call__(self, path):
        """if you want to add a path to resource uri, you can do:
        
        .. code-block:: python

            Resource("/path").get()
        """

        new_uri = self._make_uri(self.uri, path)
        return type(self)(new_uri, transport=self.transport, 
                    headers=self._headers, **self.client_opts)
 
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

    def request(self, method, path=None, payload=None, headers=None, **params):
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
        size = None
        if payload is not None:
            if isinstance(payload, file):
                try:
                    payload.flush()
                except IOError:
                    pass
                size = int(os.fstat(payload.fileno())[6])
            elif isinstance(payload, types.StringTypes):
                payload = to_bytestring(payload)
                size = len(payload)
            elif isinstance(payload, dict):
                content_type = headers.get('Content-Type')
                if content_type is not None and content_type.startswith("multipart/form-data"):
                    type_, opts = cgi.parse_header(content_type)
                    boundary = opts.get('boundary', uuid.uuid4().hex)
                    payload, headers = multipart_form_encode(payload, headers, boundary)
                else:
                    headers['Content-Type'] = "application/x-www-form-urlencoded; charset=utf-8"
                    payload = form_encode(payload)
                    size = len(payload)
            elif isinstance(payload, MultipartForm):
                headers['Content-Type'] = "multipart/form-data; boundary=%s" % payload.boundary
                headers['Content-Length'] = str(payload.get_size())
                
            if 'Content-Length' not in headers and size is not None:
                headers['Content-Length'] = size
            elif 'Content-Length' not in headers:
                raise RequestError('Unable to calculate '
                    'the length of the data parameter. Specify a value for '
                    'Content-Length')
            
            if 'Content-Type' not in headers:
                type_ = None
                if hasattr(payload, 'name'):
                    type_ = mimetypes.guess_type(payload.name)[0]
                headers['Content-Type'] = type_ and type_ or 'application/octet-stream'
                
    
        uri = self._make_uri(self.uri, path, **params)
        resp = self.transport.request(uri, method=method, body=payload, headers=headers)

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
        """Assemble a uri based on a base, any number of path segments, and query
        string parameters.

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
                _path.append(url_quote(s.strip('/'), self.charset, self.safe))
                       
        path_str =""
        if _path:
            path_str = "/".join([''] + _path)
            if trailing_slash:
                path_str = path_str + "/" 
        elif base_trailing_slash:
            path_str = path_str + "/" 
            
        if path_str:
            retval.append(path_str)

        params = []
        for k, v in query.items():
            if type(v) in (list, tuple):
                params.extend([(k, i) for i in v if i is not None])
            elif v is not None:
                params.append((k,v))
        if params:
            retval.extend(['?', url_encode(dict(params), self.charset, self.encode_keys)])

        return ''.join(retval)
                

class RestClient(object):
    """Basic rest client

        >>> res = RestClient()
        >>> xml = res.get('http://pypaste.com/about')
        >>> json = res.get('http://pypaste.com/3XDqQ8G83LlzVWgCeWdwru', headers={'accept': 'application/json'})
        >>> json.body
        u'{"snippet": "testing API.", "title": "", "id": "3XDqQ8G83LlzVWgCeWdwru", "language": "text", "revision": "363934613139"}'
    """

    

    def __init__(self, transport=None, headers=None, **client_opts):
        """Constructor for a `RestClient` object.

        RestClient represent an HTTP client.

        :param transport: any http instance of object based on 
                `restkit.transport.HTTPTransportBase`. By default it will use 
                a client based on `pycurl <http://pycurl.sourceforge.net/>`_ if 
                installed or `restkit.transport.HTTPLib2Transport`,a client based on 
                `Httplib2 <http://code.google.com/p/httplib2/>`_ or make your
                own depending of the option you need to access to the serve
                (authentification, proxy, ....).
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
            
        :param client_opts: `restkit.httpc.HttpClient` Options
        """ 
        self.headers = headers
        self.client_opts = client_opts
        self._resources = {}
        
        if transport is None:
            self.transport = HttpClient(**client_opts)
        else:
            self.transport = transport
        
        
        
    def add_authorization(self, obj_auth):
        self.transport.add_authorization(obj_auth)
        
    def get(self, uri, path=None, headers=None, **params):
        """ HTTP GET         
        
        :param uri: str, uri on which you make the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request.
        """

        return self.request('GET', uri, path=path, headers=headers, **params)

    def head(self, uri, path=None, headers=None, **params):
        """ HTTP HEAD

        see GET for params description.
        """
        return self.request("HEAD", uri, path=path, headers=headers, **params)

    def delete(self, uri, path=None, headers=None, **params):
        """ HTTP DELETE

        see GET for params description.
        """
        return self.request('DELETE', uri, path=path, headers=headers, **params)

    def post(self, uri, path=None, body=None, headers=None,  **params):
        """ HTTP POST

        :param uri: str, uri on which you make the request
        :param body: string or File object passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request
        """
        return self.request("POST", uri, path=path, body=body, 
                    headers=headers, **params)

    def put(self, uri, path=None, body=None, headers=None, **params):
        """ HTTP PUT

        see POST for params description.
        """

        return self.request('PUT', uri, path=path, body=body, 
                    headers=headers, **params)

    def request(self, method, uri, path=None, body=None, headers=None, **params):
        """ Perform HTTP call support GET, HEAD, POST, PUT and DELETE.
        
        Usage example, get friendpaste page :

        .. code-block:: python

            from restkit import RestClient
            client = RestClient()
            page = resource.request('GET', 'http://friendpaste.com')

        Or get a paste in JSON :

        .. code-block:: python

            from restkit import RestClient
            client = RestClient()
            client.request('GET', 'http://friendpaste.com/5rOqE9XTz7lccLgZoQS4IP'),
                headers={'Accept': 'application/json'})

        :param method: str, the HTTP action to be performed: 
            'GET', 'HEAD', 'POST', 'PUT', or 'DELETE'
        :param path: str or list, path to add to the uri
        :param data: tring or File object.
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request.
        
        :return: str.
        """
        
        res = Resource(uri, self.transport, self.headers)
        return res.request(method, path, payload=body, headers=headers, **params)