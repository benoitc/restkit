# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import warnings


from restkit.client import HttpConnection
from restkit.resource import Resource
from restkit.pool import ConnectionPool

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
        warnings.warn(
        "RestClient is deprecated in favor of `restkit.Resource` class.", 
        DeprecationWarning, stacklevel=2)
        
        self.headers = headers
        self.client_opts = client_opts
        self._resources = {}
        
        if transport is None:
            pool_instance = client_opts.get('pool_instance')
            if not pool_instance:
                pool = ConnectionPool(max_connections=4)
                client_opts['pool_instance'] = pool
            self.transport = HttpConnection(**client_opts)
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