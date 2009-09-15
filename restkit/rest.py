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
#
# _getCharacterEncoding from Feedparser under BSD License :
#
# Copyright (c) 2002-2006, Mark Pilgrim, All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
restkit.rest
~~~~~~~~~~~~~~~

This module provide a common interface for all HTTP equest. 

    >>> from restkit import Resource
    >>> res = Resource('http://friendpaste.com')
    >>> res.get('/5rOqE9XTz7lccLgZoQS4IP',headers={'Accept': 'application/json'})
    u'{"snippet": "hi!", "title": "", "id": "5rOqE9XTz7lccLgZoQS4IP", "language": "text", "revision": "386233396230"}'
    >>> res.status
    200
"""

import cgi
import httplib
import mimetypes
import uuid
import os
import re
import socket
import StringIO
import time
import types
import urllib

try:
    import chardet
except ImportError:
    chardet = False

from restkit.errors import *
from restkit.httpc import HttpClient, ResponseStream
from restkit.utils import to_bytestring

MIME_BOUNDARY = 'END_OF_PART'


__all__ = ['Resource', 'RestClient', 'url_quote', 'url_encode', 
'MultipartForm', 'multipart_form_encode', 'form_encode']

__docformat__ = 'restructuredtext en'

class Resource(object):
    """A class that can be instantiated for access to a RESTful resource, 
    including authentication. 

    It can use pycurl, urllib2, httplib2 or any interface over
    `restkit.http.HTTPClient`.

    """
    def __init__(self, uri, transport=None, headers=None, follow_redirect=True, 
            force_follow_redirect=False, use_proxy=False, min_size=0, 
            max_size=4, pool_class=None):
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
        :param follow_redirect: boolean, default is True, allow the client to follow redirection
        :param force_follow_redirect: boolean, default is False, force redirection on POST/PUT
        :param use_proxy: boolean, default is False, if you want to use a proxy
        :param min_size: minimum number of connections in the pool
        :param max_size: maximum number of connection in the pool
        :param pool_class: custom pool class
        """

        self.client = RestClient(transport, headers=headers, follow_redirect=follow_redirect,
            force_follow_redirect=force_follow_redirect, use_proxy=use_proxy,
            min_size=min_size, max_size=max_size, pool_class=pool_class)
        self.uri = uri
        self.transport = self.client.transport 
        self.follow_redirect = follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.use_proxy = use_proxy
        self.min_size = min_size
        self.max_size = max_size
        self.pool_class = pool_class
        self._headers = headers

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.uri)
        
    def add_authorization(self, obj_auth):
        self.client.transport.add_authorization(obj_auth)

    def clone(self):
        """if you want to add a path to resource uri, you can do:

        .. code-block:: python

            resr2 = res.clone()
        
        """
        obj = self.__class__(self.uri, transport=self.transport, headers=self._headers,
                follow_redirect=self.follow_redirect, force_follow_redirect=self.force_follow_redirect, 
                use_proxy=self.use_proxy, min_size=self.min_size, max_size=self.max_size, 
                pool_class=self.pool_class)
        return obj
   
    def __call__(self, path):
        """if you want to add a path to resource uri, you can do:
        
        .. code-block:: python

            Resource("/path").get()
        """

        return type(self)(self.client.make_uri(self.uri, path),
                transport=self.transport, headers=self._headers,
                follow_redirect=self.follow_redirect, force_follow_redirect=self.force_follow_redirect, 
                use_proxy=self.use_proxy, min_size=self.min_size, max_size=self.max_size)

    
    def get(self, path=None, headers=None, _stream=False, _stream_size=16384,
            **params):
        """ HTTP GET         
        
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request.
        """
        return self.request("GET", path=path, headers=headers, 
            _stream=_stream, _stream_size=_stream_size, **params)

    def delete(self, path=None, headers=None, **params):
        """ HTTP DELETE

        see GET for params description.
        """
        return self.request("DELETE", path=path, headers=headers, **params)

    def head(self, path=None, headers=None, **params):
        """ HTTP HEAD

        see GET for params description.
        """
        return self.request("HEAD", path=path, headers=headers, **params)

    def post(self, path=None, payload=None, headers=None, _stream=False, 
            _stream_size=16384,**params):
        """ HTTP POST

        :param payload: string passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request
        """

        return self.request("POST", path=path, payload=payload, headers=headers,
            _stream=_stream, _stream_size=_stream_size, **params)

    def put(self, path=None, payload=None, headers=None, _stream=False, 
            _stream_size=16384, **params):
        """ HTTP PUT

        see POST for params description.
        """
        return self.request("PUT", path=path, payload=payload, headers=headers, 
            _stream=_stream, _stream_size=_stream_size, **params)

    def request(self, method, path=None, payload=None, headers=None, 
            _stream=False, _stream_size=16384, **params):
        """ HTTP request

        This method may be the only one you want to override when
        subclassing `restkit.rest.Resource`.
        
        :param payload: string or File object passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param _stream: boolean, response return a ResponseStream object
        :param _stream_size: int, size in bytes of response stream block
        :param params: Optionnal parameterss added to the request
        """
        
        return self.client.request(method, self.uri, path=path,
                body=payload, headers=headers, _stream=_stream, 
                _stream_size=_stream_size, **params)

    def get_response(self):
        return self.client.get_response()
    response = property(get_response)

    def get_status(self):
        return self.client.status
    status = property(get_status)

    def update_uri(self, path):
        """
        to set a new uri absolute path
        """
        self.uri = self.client.make_uri(self.uri, 
                path)


class RestClient(object):
    """Basic rest client

        >>> res = RestClient()
        >>> xml = res.get('http://pypaste.com/about')
        >>> json = res.get('http://pypaste.com/3XDqQ8G83LlzVWgCeWdwru', headers={'accept': 'application/json'})
        >>> json
        u'{"snippet": "testing API.", "title": "", "id": "3XDqQ8G83LlzVWgCeWdwru", "language": "text", "revision": "363934613139"}'
    """

    charset = 'utf-8'
    encode_keys = True
    safe = "/:"

    def __init__(self, transport=None, headers=None, follow_redirect=True, 
            force_follow_redirect=False, use_proxy=False, min_size=0, max_size=4, 
            pool_class=None):
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
        :param follow_redirect: boolean, default is True, allow the client to follow redirection
        :param force_follow_redirect: boolean, default is False, force redirection on POST/PUT
        :param use_proxy: boolean, False, if you want to use a proxy
        :param min_size: minimum number of connections in the pool
        :param max_size: maximum number of connection in the pool
        :param pool_class: custom Pool class
        """ 

        if transport is None:
            transport = HttpClient(follow_redirect=follow_redirect, force_follow_redirect=force_follow_redirect, 
                            use_proxy=use_proxy, min_size=min_size, max_size=max_size, pool_class=pool_class)

        self.transport = transport
        self.follow_redirect=follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.use_proxy = use_proxy
        self.min_size = min_size
        self.max_size = max_size
        self.pool_class = pool_class

        self.status = None
        self.response = None
        self._headers = headers
        self._body_parts = []
        
        
    def add_authorization(self, obj_auth):
        self.transport.add_authorization(obj_auth)
        
    def get(self, uri, path=None, headers=None, _stream=False,
            _stream_size=16384, **params):
        """ HTTP GET         
        
        :param uri: str, uri on which you make the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param _stream: boolean, response return a ResponseStream object
        :param _stream_size: int, size in bytes of response stream block
        :param params: Optionnal parameterss added to the request.
        """

        return self.request('GET', uri, path=path, headers=headers, 
            _stream=_stream, _stream_size=_stream_size, **params)

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

    def post(self, uri, path=None, body=None, headers=None, _stream=False,
            _stream_size=16384, **params):
        """ HTTP POST

        :param uri: str, uri on which you make the request
        :param body: string or File object passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param _stream: boolean, response return a ResponseStream object
        :param _stream_size: int, size in bytes of response stream block
        :param params: Optionnal parameterss added to the request
        """
        return self.request("POST", uri, path=path, body=body, headers=headers, 
            _stream=_stream, _stream_size=_stream_size, **params)

    def put(self, uri, path=None, body=None, headers=None, _stream=False, 
            _stream_size=16384, **params):
        """ HTTP PUT

        see POST for params description.
        """

        return self.request('PUT', uri, path=path, body=body, headers=headers, 
            _stream=_stream, _stream_size=_stream_size, **params)

    def request(self, method, uri, path=None, body=None, headers=None, _stream=False, 
        _stream_size=16384, **params):
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
        :param _stream: boolean, response return a ResponseStream object
        :param _stream_size: int, size in bytes of response stream block
        :param params: Optionnal parameterss added to the request.
        
        :return: str.
        """

        # init headers
        
        if self._headers is not None:
            _headers = self._headers.copy()
        else:
            _headers = {}

        _headers.update(headers or {})
        
        self._body_parts = []
        size = None
        if body is not None:
            if isinstance(body, file):
                try:
                    body.flush()
                except IOError:
                    pass
                size = int(os.fstat(body.fileno())[6])
            elif isinstance(body, types.StringTypes):
                body = to_bytestring(body)
                size = len(body)
            elif isinstance(body, dict):
                content_type = _headers.get('Content-Type')
                if content_type is not None and content_type.startswith("multipart/form-data"):
                    type_, opts = cgi.parse_header(content_type)
                    boundary = opts.get('boundary', uuid.uuid4().hex)
                    body, _headers = multipart_form_encode(body, _headers, boundary)
                else:
                    _headers['Content-Type'] = "application/x-www-form-urlencoded; charset=utf-8"
                    body = form_encode(body)
                    size = len(body)
            elif isinstance(body, MultipartForm):
                _headers['Content-Type'] = "multipart/form-data; boundary=%s" % body.boundary
                _headers['Content-Length'] = str(body.get_size())
                
            if 'Content-Length' not in _headers and size is not None:
                _headers['Content-Length'] = size
            elif 'Content-Length' not in _headers:
                raise RequestError('Unable to calculate '
                    'the length of the data parameter. Specify a value for '
                    'Content-Length')
            
            if 'Content-Type' not in _headers:
                type_ = None
                if hasattr(body, 'name'):
                    type_ = mimetypes.guess_type(body.name)[0]
                _headers['Content-Type'] = type_ and type_ or 'application/octet-stream'
                
                
        
        resp, data = self.transport.request(self.make_uri(uri, path, **params), 
                        method=method, body=body, headers=_headers, 
                        stream=_stream, stream_size=_stream_size)
        self.status  = status_code = resp.status
        self.response = resp
        
        
        if status_code >= 400:
            if status_code == 404:
                raise ResourceNotFound(data, http_code=404, response=resp)
            elif status_code == 401 or status_code == 403:
                raise Unauthorized(data, http_code=status_code,
                        response=resp)
            else:
                raise RequestFailed(data, http_code=status_code,
                    response=resp)

        if isinstance(data, ResponseStream):
            return data
            
        # determine character encoding
        true_encoding, http_encoding, xml_encoding, sniffed_xml_encoding, \
        acceptable_content_type = _getCharacterEncoding(resp, data)
        

        tried_encodings = []
        # try: HTTP encoding, declared XML encoding, encoding sniffed from BOM
        for proposed_encoding in (true_encoding, xml_encoding, sniffed_xml_encoding):
            if not proposed_encoding: continue
            if proposed_encoding in tried_encodings: continue
            tried_encodings.append(proposed_encoding)
            try:
               return data.decode(proposed_encoding)
               break
            except:
                pass
                
        # if still no luck and we haven't tried utf-8 yet, try that
        if 'utf-8' not in tried_encodings:
            try:
                proposed_encoding = 'utf-8'
                tried_encodings.append(proposed_encoding)
                return data.decode(proposed_encoding)
              
            except:
                pass
                
        # if still no luck and we haven't tried windows-1252 yet, try that
        if 'windows-1252' not in tried_encodings:
            try:
                proposed_encoding = 'windows-1252'
                tried_encodings.append(proposed_encoding)
                return data.decode(proposed_encoding)
            except:
                pass
                
        # if no luck and we have auto-detection library, try that
        if chardet:
            try:
                proposed_encoding = chardet.detect(data)['encoding']
                if proposed_encoding and (proposed_encoding not in tried_encodings):
                    tried_encodings.append(proposed_encoding)
                    return data.decode(proposed_encoding)
            except:
                pass
              
        # give up, return data as is.   
        return data 

    def get_response(self):
        return self.response

    def make_uri(self, base, *path, **query):
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


# code borrowed to Wekzeug with minor changes

def url_quote(s, charset='utf-8', safe='/:'):
    """URL encode a single string with a given encoding."""
    if isinstance(s, unicode):
        s = s.encode(charset)
    elif not isinstance(s, str):
        s = str(s)
    return urllib.quote(s, safe=safe)

def url_encode(obj, charset="utf8", encode_keys=False):
    if isinstance(obj, dict):
        items = []
        for k, v in obj.iteritems():
            if not isinstance(v, (tuple, list)):
                v = [v]
            items.append((k, v))
    else:
        items = obj or ()

    tmp = []
    for key, values in items:
        if encode_keys and isinstance(key, unicode):
            key = key.encode(charset)
        else:
            key = str(key)

        for value in values:
            if value is None:
                continue
            elif isinstance(value, unicode):
                value = value.encode(charset)
            else:
                value = str(value)
        tmp.append('%s=%s' % (urllib.quote(key),
            urllib.quote_plus(value)))

    return '&'.join(tmp)
    
def form_encode(obj, charser="utf8"):
    tmp = []
    for key, value in obj.items():
        tmp.append("%s=%s" % (url_quote(key), 
                url_quote(value)))
    return to_bytestring("&".join(tmp))


class BoundaryItem(object):
    def __init__(self, name, value, fname=None, filetype=None, filesize=None):
        self.name = url_quote(name)
        if value is not None and not hasattr(value, 'read'):
            value = url_quote(value)
            self.size = len(value)
        self.value = value
        if fname is not None:
            if isinstance(fname, unicode):
                fname = fname.encode("utf-8").encode("string_escape").replace('"', '\\"')
            else:
                fname = fname.encode("string_escape").replace('"', '\\"')
        self.fname = fname
        if filetype is not None:
            filetype = to_bytestring(filetype)
        self.filetype = filetype
        
        if isinstance(value, file) and filesize is None:
            try:
                value.flush()
            except IOError:
                pass
            self.size = int(os.fstat(value.fileno())[6])
            
    def encode_hdr(self, boundary):
        """Returns the header of the encoding of this parameter"""
        boundary = url_quote(boundary)
        headers = ["--%s" % boundary]
        if self.fname:
            disposition = 'form-data; name="%s"; filename="%s"' % (self.name,
                    self.fname)
        else:
            disposition = 'form-data; name="%s"' % self.name
        headers.append("Content-Disposition: %s" % disposition)
        if self.filetype:
            filetype = self.filetype
        else:
            filetype = "text/plain; charset=utf-8"
        headers.append("Content-Type: %s" % filetype)
        headers.append("Content-Length: %i" % self.size)
        headers.append("")
        headers.append("")
        return "\r\n".join(headers)

    def encode(self, boundary):
        """Returns the string encoding of this parameter"""
        value = self.value
        if re.search("^--%s$" % re.escape(boundary), value, re.M):
            raise ValueError("boundary found in encoded string")

        return "%s%s\r\n" % (self.encode_hdr(boundary), value)
        
    def iter_encode(self, boundary, blocksize=16384):
        if not hasattr(self.value, "read"):
            yield self.encode(boundary)
        else:
            yield self.encode_hdr(boundary)
            yield self.encode(boundary)
            while True:
                block = self.value.read(blocksize)
                if not block:
                    yield "\r\n"
                    break
                yield block
                
                
class MultipartForm(object):
    
    def __init__(self, params, boundary, headers):
        self.boundary = boundary
        self.boundaries = []
        self.size = 0
        
        self.content_length = headers.get('Content-Length')
        
        if hasattr(params, 'items'):
            params = params.items()
            
        for param in params:
            name, value = param
            if hasattr(value, "read"):
                fname = getattr(value, 'name')
                if fname is not None:
                    filetype = ';'.join(filter(None, guess_type(fname)))
                else:
                    filetype = None
                if not isinstance(value, file) and self.content_length is None:
                    value = value.read()
                    
                boundary = BoundaryItem(name, value, fname, filetype)
            else:
                 boundary = BoundaryItem(name, value)
            self.boundaries.append(boundary)

    def get_size(self):
        if self.content_length is not None:
            return int(self.content_length)
        size = 0
        for boundary in self.boundaries:
            size = size + boundary.size
        return size
        
    def __iter__(self):
        for boundary in self.boundaries:
            for block in boundary.iter_encode(self.boundary):
                yield block
        yield "--%s--\r\n" % self.boundary
                    

def multipart_form_encode(params, headers, boundary):
    headers = headers or {}
    boundary = urllib.quote_plus(boundary)
    body = MultipartForm(params, boundary, headers)
    headers['Content-Type'] = "multipart/form-data; boundary=%s" % boundary
    headers['Content-Length'] = str(body.get_size())
    return body, headers



def _getCharacterEncoding(http_headers, xml_data):
    '''Get the character encoding of the XML document

    http_headers is a dictionary
    xml_data is a raw string (not Unicode)
    
    This is so much trickier than it sounds, it's not even funny.
    According to RFC 3023 ('XML Media Types'), if the HTTP Content-Type
    is application/xml, application/*+xml,
    application/xml-external-parsed-entity, or application/xml-dtd,
    the encoding given in the charset parameter of the HTTP Content-Type
    takes precedence over the encoding given in the XML prefix within the
    document, and defaults to 'utf-8' if neither are specified.  But, if
    the HTTP Content-Type is text/xml, text/*+xml, or
    text/xml-external-parsed-entity, the encoding given in the XML prefix
    within the document is ALWAYS IGNORED and only the encoding given in
    the charset parameter of the HTTP Content-Type header should be
    respected, and it defaults to 'us-ascii' if not specified.

    Furthermore, discussion on the atom-syntax mailing list with the
    author of RFC 3023 leads me to the conclusion that any document
    served with a Content-Type of text/* and no charset parameter
    must be treated as us-ascii.  (We now do this.)  And also that it
    must always be flagged as non-well-formed.  (We now do this too.)
    
    If Content-Type is unspecified (input was local file or non-HTTP source)
    or unrecognized (server just got it totally wrong), then go by the
    encoding given in the XML prefix of the document and default to
    'iso-8859-1' as per the HTTP specification (RFC 2616).
    
    Then, assuming we didn't find a character encoding in the HTTP headers
    (and the HTTP Content-type allowed us to look in the body), we need
    to sniff the first few bytes of the XML data and try to determine
    whether the encoding is ASCII-compatible.  Section F of the XML
    specification shows the way here:
    http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info

    If the sniffed encoding is not ASCII-compatible, we need to make it
    ASCII compatible so that we can sniff further into the XML declaration
    to find the encoding attribute, which will tell us the true encoding.

    Of course, none of this guarantees that we will be able to parse the
    feed in the declared character encoding (assuming it was declared
    correctly, which many are not).  CJKCodecs and iconv_codec help a lot;
    you should definitely install them if you can.
    http://cjkpython.i18n.org/
    '''

    def _parseHTTPContentType(content_type):
        '''takes HTTP Content-Type header and returns (content type, charset)

        If no charset is specified, returns (content type, '')
        If no content type is specified, returns ('', '')
        Both return parameters are guaranteed to be lowercase strings
        '''
        content_type = content_type or ''
        content_type, params = cgi.parse_header(content_type)
        return content_type, params.get('charset', '').replace("'", '')

    sniffed_xml_encoding = ''
    xml_encoding = ''
    true_encoding = ''
    http_content_type, http_encoding = _parseHTTPContentType(http_headers.get('Content-Type'))
    # Must sniff for non-ASCII-compatible character encodings before
    # searching for XML declaration.  This heuristic is defined in
    # section F of the XML specification:
    # http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info
    try:
        if xml_data[:4] == '\x4c\x6f\xa7\x94':
            # EBCDIC
            xml_data = _ebcdic_to_ascii(xml_data)
        elif xml_data[:4] == '\x00\x3c\x00\x3f':
            # UTF-16BE
            sniffed_xml_encoding = 'utf-16be'
            xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') and (xml_data[2:4] != '\x00\x00'):
            # UTF-16BE with BOM
            sniffed_xml_encoding = 'utf-16be'
            xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
        elif xml_data[:4] == '\x3c\x00\x3f\x00':
            # UTF-16LE
            sniffed_xml_encoding = 'utf-16le'
            xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and (xml_data[2:4] != '\x00\x00'):
            # UTF-16LE with BOM
            sniffed_xml_encoding = 'utf-16le'
            xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
        elif xml_data[:4] == '\x00\x00\x00\x3c':
            # UTF-32BE
            sniffed_xml_encoding = 'utf-32be'
            xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
        elif xml_data[:4] == '\x3c\x00\x00\x00':
            # UTF-32LE
            sniffed_xml_encoding = 'utf-32le'
            xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
        elif xml_data[:4] == '\x00\x00\xfe\xff':
            # UTF-32BE with BOM
            sniffed_xml_encoding = 'utf-32be'
            xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
        elif xml_data[:4] == '\xff\xfe\x00\x00':
            # UTF-32LE with BOM
            sniffed_xml_encoding = 'utf-32le'
            xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
        elif xml_data[:3] == '\xef\xbb\xbf':
            # UTF-8 with BOM
            sniffed_xml_encoding = 'utf-8'
            xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
        else:
            # ASCII-compatible
            pass
        xml_encoding_match = re.compile('^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
    except:
        xml_encoding_match = None
    if xml_encoding_match:
        xml_encoding = xml_encoding_match.groups()[0].lower()
        if sniffed_xml_encoding and (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode', 'iso-10646-ucs-4', 'ucs-4', 'csucs4', 'utf-16', 'utf-32', 'utf_16', 'utf_32', 'utf16', 'u16')):
            xml_encoding = sniffed_xml_encoding
    acceptable_content_type = 0
    application_content_types = ('application/xml', 'application/xml-dtd', 'application/xml-external-parsed-entity')
    text_content_types = ('text/xml', 'text/xml-external-parsed-entity')
    if (http_content_type in application_content_types) or \
       (http_content_type.startswith('application/') and http_content_type.endswith('+xml')):
        acceptable_content_type = 1
        true_encoding = http_encoding or xml_encoding or 'utf-8'
    elif (http_content_type in text_content_types) or \
         (http_content_type.startswith('text/')) and http_content_type.endswith('+xml'):
        acceptable_content_type = 1
        true_encoding = http_encoding or 'us-ascii'
    elif http_content_type.startswith('text/'):
        true_encoding = http_encoding or 'us-ascii'
    elif http_headers and (not http_headers.has_key('content-type')):
        true_encoding = xml_encoding or 'iso-8859-1'
    else:
        true_encoding = xml_encoding or 'utf-8'
    return true_encoding, http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type