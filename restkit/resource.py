# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


"""
restkit.resource
~~~~~~~~~~~~~~~~

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

from restkit.errors import ResourceNotFound, Unauthorized, RequestFailed,\
ResourceError, ParserError
from restkit.forms import MultipartForm, multipart_form_encode, form_encode
from restkit.client import HttpConnection
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
    max_connections = 4
    
    def __init__(self, uri, transport=None, headers=None, 
            **client_opts):
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
        :param client_opts: `restkit.client.HttpConnection` Options
        """

        pool_instance = client_opts.get('pool_instance')
        if not pool_instance:
            pool = self.pool_class(max_connections=self.max_connections)
            client_opts['pool_instance'] = pool   

        self.uri = uri
        self._headers = headers or {}
        self.client_opts = client_opts
        self._body_parts = []

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.uri)
        
    def add_authorization(self, obj_auth):
        self.transport.add_filter(obj_auth)
        
    def add_filter(self, f):
        """ add an htt filter """
        self.transport.add_filter(f)

    add_authorization = util.deprecated_property(
        add_filter, 'add_authorization', 'use add_filter() instead',
        warning=False)
        
    def remmove_filter(self, f):
        """ remove an http filter """
        self.transport.remmove_filter(f)
    

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
            raise RequestError(str(e))

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