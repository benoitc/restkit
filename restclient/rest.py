# -*- coding: utf-8 -
#
# Copyright (c) 2008 (c) Benoit Chesneau <benoitc@e-engura.com> 
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
#

"""A simple REST client"""


import httplib2
from urllib import quote, urlencode

__all__ = ['Resource', 'RestClient', 'RestClientFactory', 'ResourceNotFound', \
        'Unauthorised', 'RequestFailed']
__docformat__ = 'restructuredtext en'


class ResourceNotFound(Exception):
    """Exception raised when a 404 HTTP error is received in response to a
    request.
    """

class Unauthorised(Exception):
    """Exception raised when a 401 HTTP error is received in response to a
    request.
    """

class RequestFailed(Exception):
    """Exception raised when an unexpected HTTP error is received in response
    to a request.
    """


class Resource(object):
    """A class that can be instantiated for access to a RESTful resource, 
    including authentication.

    >>> res = Resource('http://pypaste.com/Lf68Zatx')
    >>> res.get(headers={'accept': 'application/json'})
    '{"snippet": "test", "title": "", "id": "Lf68Zatx", "language": "python", "revid": "bad17d41ea10"}'
    >>> res.status_code
    200
    >>> res = Resource('http://pypaste.com/')
    >>> post = res.post(payload='{"snippet": "test"}', headers={'accept': 'application/json', 'content-type': 'application/json'})
    >>> res.status_code
    200
    """
    def __init__(self, uri, username=None, password=None, http=None):
        self.client = RestClient(username, password, http)
        self.uri = uri
        self.http = http

    def delete(self, path=None, headers=None, **params):
        return self.client.delete(self.uri, path=path, headers=headers, **params)

    def get(self, path=None, headers=None, **params):
        return self.client.get(self.uri, path=path, headers=headers, **params)

    def head(self, path=None, headers=None, **params):
        return self.client.head(self.uri, path=path, headers=headers, **params)

    def post(self, payload=None, path=None, headers=None, **params):
        return self.client.post(self.uri, path=path, body=payload, headers=headers, **params)

    def put(self, payload=None, path=None, headers=None, **params):
        return self.client.put(self.uri, path=path, body=payload, headers=headers, **params)

    def get_status_code(self):
        return self.client.status_code
    status_code = property(get_status_code)

    def get_message_error(self):
        return self.client.error
    error = property(get_message_error)


class RestClient(object):
    """Basic rest client
    >>> res = RestClient()
    >>> xml = res.get('http://pypaste.com/about')
    >>> json = res.get('http://pypaste.com/Lf68Zatx', headers={'accept': 'application/json'})
    >>> json
    '{"snippet": "test", "title": "", "id": "Lf68Zatx", "language": "python", "revid": "bad17d41ea10"}'
    """
    
    def __init__(self, username=None, password=None, http=None):
        if http is None:
            http = httplib2.Http()
            http.force_exception_to_status_code = False
        self.http = http
        self.username = username
        self.password = password
        if self.username is not None and self.password is not None:
            self.http.add_credentials(username, password)

        self.status_code = None
        self.response = None

    def delete(self, uri, path=None, headers=None, **params):
        return self.make_request('DELETE', uri, path=path, headers=headers, **params)

    def get(self, uri, path=None, headers=None, **params):
        return self.make_request('GET', uri, path=path, headers=headers, **params)

    def head(self, uri, path=None, headers=None, **params):
        return self.make_request("HEAD", uri, path=path, headers=headers, **params)

    def post(self, uri, path=None, body=None, headers=None, **params):
        return self.make_request('POST', uri, path=path, body=body, headers=headers,
                             **params)

    def put(self, uri, path=None, body=None, headers=None, **params):
        return self.make_request('PUT', uri, path=path, body=body, headers=headers,
                             **params)

    def make_request(self, method, uri, path=None, body=None, headers=None, **params):
        headers = headers or {}

        # body should never be null
        if body is None:
            body = ""

        resp, data = self.http.request(make_uri(uri, path, **params), method,
                body=body, headers=headers)

        self.status_code = int(resp.status)
        self.response = resp

        if self.status_code >= 400:
            if type(data) is dict:
                error = (data.get('error'), data.get('reason'))
            else:
                error = data

            self.error = error

            if self.status_code == 404:
                raise ResourceNotFound(error)
            elif self.status_code == 401:
                raise Unauthorized
            else:
                raise RequestFailed((self.status_code, error))

        return data


def make_uri(base, *path, **query):
    """Assemble a uri based on a base, any number of path segments, and query
    string parameters.

    >>> make_uri('http://example.org/', '/_all_dbs')
    'http://example.org/_all_dbs'
    """

    if base and base.endswith("/"):
        base = base[:-1]
    retval = [base]

    # build the path
    path = '/'.join([''] +
                    [unicode_quote(s.strip('/')) for s in path
                     if s is not None])
    if path:
        retval.append(path)

    params = []
    for k, v in query.items():
        if type(v) in (list, tuple):
            params.extend([(name, i) for i in v if i is not None])
        elif v is not None:
            params.append((k,v))
    if params:
        retval.extend(['?', unicode_urlencode(params)])
    return ''.join(retval)

def unicode_quote(string, safe=''):
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return quote(string, safe)

def unicode_urlencode(data):
    if isinstance(data, dict):
        data = data.items()
    params = []
    for name, value in data:
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        params.append((name, value))
    return urlencode(params)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

