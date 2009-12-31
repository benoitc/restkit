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
import gzip
import httplib
import re
import socket
from StringIO import StringIO
import types
import urlparse
import zlib

import restkit
from restkit import errors

from restkit import pool
from restkit.utils import to_bytestring


MAX_CHUNK_SIZE = 16384
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
    
    def depth(self, uri):
        return uri.path.count("/")
        
    def inscope(self, hostname, uri):
        """ if you want to set multiple authorization on an
        http client depending on hostname or uri"""
        return True
        
    def request(self, uri, method, body, headers):
        """ path auth info to the request """
        pass
        
    def response(self, response):
        """ allow us to store new auth info from the response.
        if something is wrong, should return True to redo 
        the request. Else return False.
        """
        return False

class BasicAuth(Auth):
    """ basic authentification """
    
    def __init__(self, username, password):
        self.credentials = (username, password)
    
    def request(self, uri, method, body, headers):
        headers['authorization'] = 'Basic ' + base64.encodestring("%s:%s" % self.credentials)[:-1]

class HTTPResponse(object):
    """ Object containing response."""
    
    charset = "utf8"
    unicode_errors = 'strict'
    
    def __init__(self, response, release_callback):
        self.resp = response
        self.release_callback = release_callback
        self.headerslist = response.getheaders()
        self.status = "%s %s" % (response.status, response.reason)
        self.status_int = response.status
        self.version = response.version
        
        headers = {}
        for key, value in self.headerslist:
            headers[key.lower()] = value
        self.headers = headers
        self.closed = False
        self._body = ""
            
    def get_body(self, stream=False):
        if self._body:
            return self._body
        body = _decompress_content(self, stream=stream)
        if not stream:
            self._body = body
        return body

    @property
    def unicode_body(self):
        if not self.charset:
            raise AttributeError(
                "You cannot access HTTPResponse.unicode_body unless charset is set")
        body = self.get_body()
        return body.decode(self.charset, self.unicode_errors)

    @property
    def body(self):
        """ get body in one bytestring """
        return self.get_body()
    
    @property
    def body_file(self):
        """ get body as a file object """
        return self.get_body(stream=True)
        
    def close(self):
        """ close the response"""
        if not self.closed:
            self.closed = True
            self.release_callback()
            if not self.resp.isclosed():
                self.resp.close()


#TODO : manage authentification detection
class HttpClient(object):
    max_redirections = 5
    pool_class = pool.ConnectionPool
    response_class = HTTPResponse
     
    def __init__(self, follow_redirect=True, force_follow_redirect=False, 
            response_class=None, pool_class=None, **conn_opts):
        self.authorizations = []
        self.use_proxy = conn_opts.get("use_proxy", False)
        self.follow_redirect = follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.conn_opts = conn_opts
        self._http_pool = {}
        if response_class is not None:
            self.response_class = response_class
        if pool_class is not None:
            self.pool_class = pool_class

    def add_authorization(self, obj_auth):
        self.authorizations.append(obj_auth)
        
    def _get_pool(self, uri):
        conn_key = (uri.scheme, uri.netloc, self.use_proxy)
        if conn_key in self._http_pool:
            pool = self._http_pool[conn_key]
        else:
            pool = self.pool_class(uri, **self.conn_opts)
            self._http_pool[conn_key] = pool
        return pool

    def _get_connection(self, uri):
        pool = self._get_pool(uri)
        return  pool.get()
        
    def _release_connection(self, uri, connection):
        pool = self._get_pool(uri)
        pool.put(connection)
        
    def _clean_pool(self, uri):
        pool = self._get_pool(uri)
        pool.clear()
        
    def _make_request(self, uri, method, body, headers): 
        for i in range(2):
            connection = self._get_connection(uri)
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
                        
                    if isinstance(body, types.StringTypes) or hasattr(body, 'read'):
                        _send_body_part(body, connection)
                    elif hasattr(body, "__iter__"):
                        for body_part in body:
                            _send_body_part(body_part, connection)
                    elif isinstance(body, list):
                        for body_part in body:
                            _send_body_part(body_part, connection)
                    else:
                        _send_body_part(body, connection)
                response = connection.getresponse()
            except socket.gaierror, e:
                self._clean_pool(uri)
                raise errors.ResourceNotFound("Unable to find the server at %s" % connection.host, 404)
            except (socket.error, httplib.BadStatusLine), e:
                # we should do better error parsing here
                self._clean_pool(uri)
                if i == 0:
                    continue
                else:
                    raise errors.RequestFailed("socket error %s" % str(e), 500)
            break
                    
        # Return the HTTP Response from the server.
        return response, connection
        
    def _request(self, uri, method, body, headers, nb_redirections=0):
        auths = [(auth.depth(uri), auth) for auth in self.authorizations if auth.inscope(uri.hostname, uri)]
        auth = auths and sorted(auths)[0][1] or None
        if auth:
            auth.request(uri, method, body, headers)
            
        headers = _normalize_headers(headers)
        
        response, connection = self._make_request(uri, method, body, headers)
        
        if auth and auth.response(response):
            auth.request(uri, method, headers, body)
            response, connection = self._make_request(uri, method, body, headers)
            
        if self.follow_redirect:
            if nb_redirections < self.max_redirections: 
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
        
    def request(self, url, method='GET', body=None, headers=None):  
        headers = headers or {}
        uri = url_parser(url)
        self.final_url = url
        
        headers.setdefault('User-Agent', restkit.USER_AGENT)
        if method in ["POST", "PUT"] and body is None:
            headers.setdefault("Content-Length", "0")
            
        if self.use_proxy and uri.scheme != "https":
            proxy_auth = pool.get_proxy_auth()
            if proxy_auth:
                headers['Proxy-Authorization'] = proxy_auth.strip()
            
        response, connection = self._request(uri, method, body, headers)
        release_callback =  lambda: self._release_connection(uri, connection)
        resp = self.response_class(response, release_callback)
        resp.final_url = self.final_url
        
        if method == "HEAD":
            resp.close()
        return resp
     
def _complain_ifclosed(closed):
    if closed:
        raise ValueError, "I/O operation on closed response"        
            
class ResponseStream(object):
    
    def __init__(self, response):
        self.response = response
        self.resp = response.resp
        self._rbuf = ''
        self.stream_size = MAX_CHUNK_SIZE
        
    def close(self):
        if not self.response.closed:
            self._buffer = ""
            self.response.close()
        
    def read(self, amt=None):
        if self._rbuf and not amt is None:
            L = len(self._rbuf)
            if amt > L:
                amt -= L
            else:
                s = self._rbuf[:amt]
                self._rbuf = self._rbuf[amt:]
                return s
        data = self.resp.read(amt)
        if not data:
            self.close()
        s = self._rbuf + data
        self._rbuf = ''
        return s

    def readline(self, amt=-1):
        i = self._rbuf.find('\n')
        while i < 0 and not (0 < amt <= len(self._rbuf)):
            new = self.resp.read(self.stream_size)
            if not new: 
                self.close()
                break
            i = new.find('\n')
            if i >= 0: 
                i = i + len(self._rbuf)
            self._rbuf = self._rbuf + new
        if i < 0: 
            i = len(self._rbuf)
        else: 
            i = i+1
        if 0 <= amt < len(self._rbuf): 
            i = amt
        data, self._rbuf = self._rbuf[:i], self._rbuf[i:]
        return data

    def readlines(self, sizehint=0):
        total = 0
        lines = []
        line = self.readline()
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline()
        return lines
    
    def next(self):
        r = self.readline()
        if not r:
            raise StopIteration
        return r
        
    def __iter__(self):
        return self

def _get_content(response):
    data = response.resp.read()
    response.close()
    return data

def _decompress_content(response, stream=False):
    resp = response.resp
    try:
        encoding = response.headers.get('content-encoding', None)
        if encoding in ('gzip', 'deflate'):
            if encoding == 'gzip':
                if stream:
                    return gzip.GzipFile(fileobj=ResponseStream(response))
                else:
                    data =  gzip.GzipFile(fileobj=ResponseStream(response)).read()
                    response.close()
                    return data
            else:
                if stream:
                    return ResponseStream(ResponseStream(response))
                else:
                    return zlib.decompress(_get_content(response))
        else:
            if stream:
                return ResponseStream(response)
            else:
                return _get_content(response)
    except Exception, e:
        response.close()
        raise errors.ResponseError("Decompression failed %s" % str(e))
        
        
def _send_body_part(data, connection):
    if isinstance(data, types.StringTypes):
        data = StringIO(to_bytestring(data))
    elif not hasattr(data, 'read'):
        data = StringIO(str(data))
    
    # we always stream
    while 1:
        binarydata = data.read(16384)
        if binarydata == '': break
        connection.send(binarydata)