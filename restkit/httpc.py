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
# 
# ProxiedHttpClient code from Google GData Python client under Apache License 2
# Copyright (C) 2006-2009 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import copy
import httplib
import os
import re
import socket
import StringIO
import types
import urllib
import urlparse

import restkit
from restkit import errors
from restkit.pool import ConnectionPool, get_proxy_auth
from restkit.utils import to_bytestring


url_parser = urlparse.urlparse

NORMALIZE_SPACE = re.compile(r'(?:\r\n)?[ \t]+')
def _normalize_headers(headers):
    return dict([ (key.lower(), NORMALIZE_SPACE.sub(str(value), ' ').strip())  for (key, value) in headers.iteritems()])

def _relative_uri(uri):
    if not uri.path:
        path = "/"
    else:
        path = uri.path
    if uri.query:
        return path + "?" + uri.query
    return path


class Auth(object):
    """ Interface for Auth classes """
    def __init__(self, credentials, **kwargs):
        self.credentials = credentials
        
    def depth(self, uri):
        return uri.path.count("/")
        
    def inscope(self, hostname, uri):
        """ if you want to set multiple authorization on an
        http client depending on hostname or uri"""
        return True
        
    def request(self, uri, method, body, headers):
        pass
        
    def response(self, response, content):
        """ allow us to store new auth info from the response."""
        return False
        
    def add_credentials(self, *args, **kwargs):
        raise NotImplementedError

class BasicAuth(Auth):
    """ basic authentification """
    def request(self, uri, method, body, headers):
        headers['authorization'] = 'Basic ' + base64.b64encode("%s:%s" % self.credentials).strip()
        
    def add_credentials(self, username, password=None):
        password = password or ""
        self.credentials = (username, password)

#TODO : manage authentification detection
class HttpClient(object):
    MAX_REDIRECTIONS = 5
    
    def __init__(self, follow_redirect=True, force_follow_redirect=False,
            use_proxy=False, min_size=0, max_size=4, pool_class=None):
        self.authorizations = []
        self.use_proxy = use_proxy
        self.follow_redirect = follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.min_size = min_size
        self.max_size = max_size
        self.connections = {}
        if pool_class is None:
            self.pool_class = ConnectionPool
        else:
            self.pool_class = pool_class
        
    def add_authorization(self, obj_auth):
        self.authorizations.append(obj_auth)
        
    def _get_connection(self, uri, headers=None):
        connection = None
        conn_key = (uri.scheme, uri.netloc, self.use_proxy)

        if conn_key in self.connections:
            pool = self.connections[conn_key]
        else:
            pool = self.connections[conn_key] = self.pool_class(uri, self.use_proxy)
        connection = pool.get()
        return connection
        
    def _release_connection(self, uri, connection):
        conn_key = (uri.scheme, uri.netloc, self.use_proxy)

        if conn_key in self.connections:
            pool = self.connections[conn_key]
        else:
            pool = self.connections[conn_key] =self.pool_class(uri, self.use_proxy)
        pool.put(connection)

            
    def _make_request(self, uri, method, body, headers): 
        for i in range(2):
            connection = self._get_connection(uri, headers)
            connection.debuglevel = restkit.debuglevel
            try:
                if connection.host != uri.hostname:
                    connection.putrequest(method, uri.geturl())
                else:
                    connection.putrequest(method, _relative_uri(uri))
        
                # bug in Python 2.4 and 2.5
                # httplib.HTTPConnection.putrequest adding 
                # HTTP request header 'Host: domain.tld:443' instead of
                # 'Host: domain.tld'
                if (uri.scheme == 'https' and (uri.port or 443) == 443 and
                        hasattr(connection, '_buffer') and
                        isinstance(connection._buffer, list)):
                    header_line = 'Host: %s:443' % uri.hostname
                    replacement_header_line = 'Host: %s' % uri.hostname
                    try:
                        connection._buffer[connection._buffer.index(header_line)] = (
                            replacement_header_line)
                    except ValueError:  # header_line missing from connection._buffer
                        pass
        
                # Send the HTTP headers.
                for header_name, value in headers.iteritems():
                    connection.putheader(header_name, value)
                connection.endheaders()
        
                if body is not None:
                    if i > 0 and hasattr(body, 'seek'):
                        body.seek(0)
                        
                    if isinstance(body, types.StringTypes) and len(body) == 0:
                        connection.send("")
                    elif isinstance(body, types.StringTypes) or hasattr(body, 'read'):
                        _send_body_part(body, connection)
                    elif hasattr(body, "__iter__"):
                        for body_part in body:
                            _send_body_part(body_part, connection)
                    elif isinstance(body, list):
                        for body_part in body:
                            _send_body_part(body_part, connection)
                    else:
                        _send_body_part(body, connection)
                    
            except socket.gaierror:
                connection.close()
                raise errors.ResourceNotFound("Unable to find the server at %s" % connection.host, 404)
            except (socket.error, httplib.HTTPException):
                connection.close()
                if i == 0:
                    continue
                else:
                    raise
            break
                    
        # Return the HTTP Response from the server.
        return connection
        
    def _request(self, uri, method, body, headers, nb_redirections=0):
        auths = [(auth.depth(uri), auth) for auth in self.authorizations if auth.inscope(uri.hostname, uri)]
        auth = auths and sorted(auths)[0][1] or None
        if auth:
            auth.request(uri, method, body, headers)
            
        headers = _normalize_headers(headers)
        old_response = None
        
        connection = self._make_request(uri, method, body, headers)
        response = connection.getresponse()
        
        if auth and auth.response(response, body):
            auth.request(uri, method, headers, body)
            connection = self._make_request(uri, method, body, headers)
            response = connection.getresponse()
            
        if self.follow_redirect:
            if nb_redirections < self.MAX_REDIRECTIONS: 
                if response.status in [301, 302, 307]:
                    if method in ["GET", "HEAD"] or self.force_follow_redirect:
                        if method not in ["GET", "HEAD"] and hasattr(body, 'seek'):
                            body.seek(0)
                        
                        new_url = response.getheader('location')
                        new_uri = url_parser(new_url)
                        if not new_uri.netloc: # we got a relative url
                            absolute_uri = "%s://%s" % (uri.scheme, uri.netloc)
                            new_url = urlparse.urljoin(absolute_uri, new_url)
                        self._release_connection(uri, connection)
                        response, connection = self._request(url_parser(new_url), method, body, 
                            headers, nb_redirections + 1)
                        self.final_url = new_url
                elif response.status == 303: 
                    # only 'GET' is possible with this status
                    # according the rfc
                    new_url = response.getheader('location')
                    if not new_uri.netloc: # we got a relative url
                        absolute_uri = "%s://%s" % (uri.scheme, uri.netloc)
                        new_uri = url_parser(new_url)
                        new_url = urlparse.urljoin(absolute_uri, new_url)
                    self._release_connection(uri, connection)
                    response, connection = self._request(url_parser(new_url), 'GET', headers, nb_redirections + 1)
                    self.final_url = new_url
            else:
                raise errors.RedirectLimit("Redirection limit is reached")
        return response, connection
        
    def request(self, url, method='GET', body=None, headers=None, stream=False, 
            stream_size=16384):  
        headers = headers or {}
        uri = url_parser(url)
        self.final_url = url
        
        headers.setdefault('User-Agent', restkit.USER_AGENT)
        if method in ["POST", "PUT"] and body is None:
            body = ""
            headers.setdefault("Content-Length", str(len(body)))
            
        if self.use_proxy and uri.scheme != "https":
            proxy_auth = get_proxy_auth()
            if proxy_auth:
                headers['Proxy-Authorization'] = proxy_auth.strip()
            
        response, connection = self._request(uri, method, body, headers)
        resp = HTTPResponse(response)
        resp.final_url = self.final_url
        
        if method == "HEAD":
            connection.close()
            return resp, ""
        else:
            return resp, _decompress_content(resp, response, 
                lambda: self._release_connection(uri, connection), 
                stream, stream_size)
                
def _decompress_content(resp, response, release_callback, stream=False, stream_size=16384):
    try:
        encoding = resp.get('content-encoding', None)
        if encoding in ['gzip', 'deflate']:
            
            if encoding == 'gzip':
                compressedstream = StringIO.StringIO(response.read())
                release_callback()
                data = gzip.GzipFile(fileobj=compressedstream)
                if stream:
                    return ResponseStream(data, stream_size)
                else:
                    return data.read()
            else:
                data =  zlib.decompress(response.read())
                release_callback()
                if stream:
                    return ResponseStream(StringIO.StringIO(data), stream_size)
                else:
                    return data
        else:
            if stream:
                return ResponseStream(response, stream_size, release_callback)
            else:
                data = response.read()
                release_callback()
                return data
    except Exception, e:
        raise errors.ResponseError("Decompression failed %s" % str(e))
        
        
def _send_body_part(data, connection):
    if isinstance(data, types.StringTypes):
        data = StringIO.StringIO(to_bytestring(data))
    elif not hasattr(data, 'read'):
        data = StringIO.StringIO(str(data))
    
    # we always stream
    while 1:
        binarydata = data.read(100000)
        if binarydata == '': break
        connection.send(binarydata)
        
        
class ResponseStream(object):
    
    def __init__(self, response, amnt=16384, release_callback=None):
        self.response = response
        self.amnt = amnt
        self.callback = release_callback
        
    def next(self):
        return self.response.read(self.amnt)
            
    def __iter__(self):
        while 1:
            data = self.next()
            if data:
                yield data
            else:
                break
        if self.callback is not None:
            self.callback()
        
class HTTPResponse(dict):
    """An object more like email.Message than httplib.HTTPResponse.
    
        >>> from restclient import Resource
        >>> res = Resource('http://e-engura.org')
        >>> from restclient import Resource
        >>> res = Resource('http://e-engura.org')
        >>> page = res.get()
        >>> res.status
        200
        >>> res.response['content-type']
        'text/html'
        >>> logo = res.get('/images/logo.gif')
        >>> res.response['content-type']
        'image/gif'
    """

    final_url = None
    
    "Status code returned by server. "
    status = 200

    """Reason phrase returned by server."""
    reason = "Ok"

    def __init__(self, info):
        if hasattr(info, "getheaders"):
            for key, value in info.getheaders():
                self[key.lower()] = value
            self.status = info.status
            self['status'] = str(self.status)
            self.reason = info.reason
            self.version = info.version
        else:
            print info
            for key, value in info.iteritems(): 
                self[key.lower()] = value 
            self.status = int(self.get('status', self.status))
            
        self.final_url = self.get('final_url', self.final_url)

    def __getattr__(self, name):
        if name == 'dict':
            return self 
        else:  
            raise AttributeError, name

    def __repr__(self):
        return "<%s status %s for %s>" % (self.__class__.__name__,
                                          self.status,
                                          self.final_url)
