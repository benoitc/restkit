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

import base64
import copy
import httplib
import re
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
    def __init__(self, credentials, headers=None, **kwargs):
        self.credentials = credentials
        self.headers = headers or {}
        
    def depth(self, uri):
        return uri.path.count("/")
        
    def inscope(self, hostname, uri):
        """ if you want to set multiple authorization on an
        http client depending on hostname or uri"""
        return True
        
    def request(self, url, method, body, headers):
        pass
        
    def response(self, response, content):
        """ allow us to store new auth info from the response."""
        return False
        
    def add_credentials(self, *args, **kwargs):
        raise NotImplementedError

class BasicAuth(Auth):
    """ basic authentification """
    def request(self, url, method, body, headers):
        headers['authorization'] = 'Basic ' + base64.b64encode("%s:%s" % self.credentials).strip()
        
    def add_credentials(self, username, password=None):
        password = password or ""
        self.credentials = (username, password)

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
        
        if body:
            if isinstance(body, types.StringTypes) or hasattr(body, 'read'):
                _send_body_part(body, connection)
            else:
                for part in body_parts:
                    _send_body_part(part, connection)
                    
        # Return the HTTP Response from the server.
        return connection.getresponse()
        
    def request(self, url, method='GET', body=None, headers=None, stream=False, stream_size=16384,
            nb_redirections=0):  
        headers = headers or {}
        uri = url_parser(url)
        
        headers.setdefault('User-Agent', restkit.USER_AGENT)
        auths = [(auth.depth(uri), auth) for auth in self.authorizations if auth.inscope(uri.hostname, uri)]
        auth = auths and sorted(auths)[0][1] or None
        if auth:
            auth.request(url, method, body, headers)
            
        headers = _normalize_headers(headers)
        old_response = None
        
        response = self._make_request(uri, method, body, headers)
        
        if auth and auth.response(response, body):
            auth.request(method, request_uri, headers, body)
            response = self._make_request(conn, request_uri, method, body, headers)
            
            
        if self.follow_redirect:
            if nb_redirections < self.MAX_REDIRECTIONS: 
                if response.status in [301, 302, 307]:
                    if method in ["GET", "HEAD"] or self.force_follow_redirect:
                        old_response = copy.deepcopy(response)
                        new_url = response['location']
                        response = self.request(new_url, method, body, headers, 
                            nb_redirections + 1)
                elif response.status == 303:
                    new_url = response['location']
                    response = self.request(new_url, 'GET', headers)
            else:
                raise errors.RedirectLimit("Redirection limit is reached")
        
        resp = HTTPResponse(response)
        if method == "HEAD":
            return resp, ""
        else:
            return resp, _decompress_content(resp, response, stream, stream_size)
            if stream:
                return resp, ResponseStream(response, stream_size)
            return resp, response.read()
        
        
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
    except:
        raise errors.ResponseError("Decompression failed")
        
        
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