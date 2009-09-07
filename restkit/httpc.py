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
    
    def __init__(self, follow_redirect=True, force_follow_redirect=False):
        self.authorizations = []
        self.use_proxy = False
        self.follow_redirect = follow_redirect
        self.force_follow_redirect = force_follow_redirect
        
    def add_authorization(self, obj_auth):
        self.authorizations.append(obj_auth)
        
    def _get_connection(self, uri, headers=None):
        connection = None
        if uri.scheme == 'https':
            if not uri.port:
                connection = httplib.HTTPSConnection(uri.hostname)
            else:
                connection = httplib.HTTPSConnection(uri.hostname, uri.port)
        else:
            if not uri.port:
                connection = httplib.HTTPConnection(uri.hostname)
            else:
                connection = httplib.HTTPConnection(uri.hostname, uri.port)
        return connection
        
        
    def _make_request(self, uri, method, body, headers):
        connection = self._get_connection(uri, headers)
        connection.debuglevel = restkit.debuglevel
        
        for i in range(2):
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
                if i == 0:
                    connection.close()
                    continue
                else:
                    raise
            break
                    
        # Return the HTTP Response from the server.
        return connection.getresponse()
        
    def _request(self, uri, method, body, headers, nb_redirections=0):
        auths = [(auth.depth(uri), auth) for auth in self.authorizations if auth.inscope(uri.hostname, uri)]
        auth = auths and sorted(auths)[0][1] or None
        if auth:
            auth.request(uri, method, body, headers)
            
        headers = _normalize_headers(headers)
        old_response = None
        
        response = self._make_request(uri, method, body, headers)
            
        if auth and auth.response(response, body):
            auth.request(uri, method, headers, body)
            response = self._make_request(uri, method, body, headers)

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
                        response = self._request(url_parser(new_url), method, body, 
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
                    response = self._request(url_parser(new_url), 'GET', headers, nb_redirections + 1)
                    self.final_url = new_url
            else:
                raise errors.RedirectLimit("Redirection limit is reached")
        return response
        
    def request(self, url, method='GET', body=None, headers=None, stream=False, 
            stream_size=16384):  
        headers = headers or {}
        uri = url_parser(url)
        self.final_url = url
        
        headers.setdefault('User-Agent', restkit.USER_AGENT)
        if method in ["POST", "PUT"] and body is None:
            body = ""
            headers.setdefault("Content-Length", str(len(body)))

        response = self._request(uri, method, body, headers)
        resp = HTTPResponse(response)
        resp.final_url = self.final_url
        
        if method == "HEAD":
            return resp, ""
        else:
            return resp, _decompress_content(resp, response, stream, stream_size)
            if stream:
                return resp, ResponseStream(response, stream_size)
            return resp, response.read()
        
class ProxiedHttpClient(HttpClient):
    """ HTTP Client with simple proxy management """

    def _get_connection(self, uri, headers=None):
        headers = headers or {}
        proxy = None
        if uri.scheme == 'https':
            proxy = os.environ.get('https_proxy')
        elif uri.scheme == 'http':
            proxy = os.environ.get('http_proxy')

        if not proxy:
            return HttpClient._get_connection(self, uri, headers=headers)

        proxy_auth = _get_proxy_auth()
        if uri.scheme == 'https':
            if proxy_auth:
                proxy_auth = 'Proxy-authorization: %s' % proxy_auth
            port = uri.port
            if not port:
                port = 443
            proxy_connect = 'CONNECT %s:%s HTTP/1.0\r\n' % (uri.hostname, port)
            user_agent = 'User-Agent: %s\r\n' % (headers.get('User-Agent', restkit.USER_AGENT))
            proxy_pieces = '%s%s%s\r\n' % (proxy_connect, proxy_auth, user_agent)
            proxy_uri = url_parser(proxy)
            if not proxy_uri.port:
                proxy_uri.port = '80'
            # Connect to the proxy server, very simple recv and error checking
            p_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            p_sock.connect((proxy_uri.host, int(proxy_uri.port)))
            p_sock.sendall(proxy_pieces)
            response = ''
            # Wait for the full response.
            while response.find("\r\n\r\n") == -1:
                response += p_sock.recv(8192)
            p_status = response.split()[1]
            if p_status != str(200):
                raise ProxyError('Error status=%s' % str(p_status))
            # Trivial setup for ssl socket.
            ssl = socket.ssl(p_sock, None, None)
            fake_sock = httplib.FakeSocket(p_sock, ssl)
            # Initalize httplib and replace with the proxy socket.
            connection = httplib.HTTPConnection(proxy_uri.host)
            connection.sock=fake_sock
            return connection
        else:
            proxy_uri = url_parser(proxy)
            if not proxy_uri.port:
                proxy_uri.port = '80'
            if proxy_auth:
                headers['Proxy-Authorization'] = proxy_auth.strip()
            return httplib.HTTPConnection(proxy_uri.hostname, proxy_uri.port)
        return None
            
def _decompress_content(resp, response, stream=False, stream_size=16384):
    try:
        encoding = resp.get('content-encoding', None)
        if encoding in ['gzip', 'deflate']:
            
            if encoding == 'gzip':
                compressedstream = StringIO.StringIO(response.read())
                data = gzip.GzipFile(fileobj=compressedstream)
                if stream:
                    return ResponseStream(data, stream_size)
                else:
                    return data.read()
            else:
                data =  zlib.decompress(response.read())
                if stream:
                    return ResponseStream(StringIO.StringIO(data), stream_size)
                else:
                    return data
        else:
            if stream:
                return ResponseStream(response, stream_size)
            else:
                return response.read()
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
        
def _get_proxy_auth():
  import base64
  proxy_username = os.environ.get('proxy-username')
  if not proxy_username:
    proxy_username = os.environ.get('proxy_username')
  proxy_password = os.environ.get('proxy-password')
  if not proxy_password:
    proxy_password = os.environ.get('proxy_password')
  if proxy_username:
    user_auth = base64.b64encode('%s:%s' % (proxy_username,
                                            proxy_password))
    return 'Basic %s\r\n' % (user_auth.strip())
  else:
    return ''
        
class ResponseStream(object):
    
    def __init__(self, response, amnt=16384):
        self.response = response
        self.amnt = amnt
        
    def next(self):
        try:
            self.response.read(amnt)
        except:
            raise errors.ResponseError("Error while getting response")
            
    def __iter__(self):
        while 1:
            data = self.next()
            if data:
                yield data
            else:
                break
        
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
        if isinstance(info, httplib.HTTPResponse):
            for key, value in info.getheaders():
                self[key.lower()] = value
            self.status = info.status
            self['status'] = str(self.status)
            self.reason = info.reason
            self.version = info.version
        else:
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
