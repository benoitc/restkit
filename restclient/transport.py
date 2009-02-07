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

import codecs
import StringIO
import httplib

import re
import sys

import restclient
from restclient.utils import to_bytestring, iri2uri

try:
    import httplib2
except ImportError:
    httplib2 = None

# try to import pycurl, which will let use of CurlHttpClient
try:
    import pycurl
except ImportError:
    pycurl=None

_default_http = None

class TransportError(Exception):
    """Error raised by a transport """

USER_AGENT = "py-restclient/%s (%s)" % (restclient.__version__, sys.platform)
DEFAULT_MAX_REDIRECT = 3

NORMALIZE_SPACE = re.compile(r'(?:\r\n)?[ \t]+')
def _normalize_headers(headers):
    return dict([ (key.lower(), NORMALIZE_SPACE.sub(value, ' ').strip())  for (key, value) in headers.iteritems()])



def createHTTPTransport():
    """Create default HTTP client instance
    prefers Curl to urllib"""

    if pycurl is None:
        http = HTTPLib2Transport()
    else:
        http = CurlTransport()

    return http

def getDefaultHTTPTransport():
    """ Return the default http transport instance instance
    if no client has been set, it will create a default client.

    :return: the default client
    """
    global _default_http

    if _default_http is None:
        setDefaultHTTPTransport(createHTTPTransport())

    return _default_http

def setDefaultHTTPTransport(httptransport):
    """ set default http transport 
    :param http: RestClient
    """
    global _default_http

    _default_http = httptransport

def useCurl():
    global _default_http
    if _default_http is None:
        setDefaultHTTPTransport(createHTTPTransport())

    return isinstance(_default_http, CurlTransport)

class HTTPError(Exception):
    """ raised when there is an HTTP error """

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
        for key, value in info.iteritems(): 
            self[key] = value 
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




class HTTPTransportBase(object):
    """ Interface for HTTP clients """

    def __init__(self, proxy_infos=None):
        """ constructor for HTTP transport interface

        :param proxy_infos: dict, infos to connect via proxy:

        .. code-block:: python

            {
                'proxy_user': 'XXXXXXX',
                'proxy_password': 'XXXXXXX',
                'proxy_host': 'proxy',
                'proxy_port': 8080,
            }
        """
        self._credentials = {}
        self.proxy_infos = proxy_infos or {}

    def request(self, url, method='GET', body=None, headers=None):
        """Perform HTTP call and manage , support GET, HEAD, POST, PUT and
        DELETE

        :param url: url on which to perform the actuib
        :param body: str
        :param headers: dict, optionnal headers that will
            be added to HTTP request

        :return: object representing HTTP Response
        """
        raise NotImplementedError

    def add_credentials(self, user, password):
        self._credentials = {
                "user": user,
                "password": password
        }

    def _get_credentials(self):
        return self._credentials


def _get_pycurl_errcode(symbol, default):
    """
    Returns the numerical error code for a symbol defined by pycurl.

    Different pycurl implementations define different symbols for error
    codes. Old versions never define some symbols (wether they can return the
    corresponding error code or not). The following addresses the problem by
    defining the symbols we care about.  Note: this allows to define symbols
    for errors that older versions will never return, which is fine.
    """
    return pycurl.__dict__.get(symbol, default)

if pycurl is not None:
    CURLE_COULDNT_CONNECT = _get_pycurl_errcode('E_COULDNT_CONNECT', 7)
    CURLE_COULDNT_RESOLVE_HOST = _get_pycurl_errcode('E_COULDNT_RESOLVE_HOST', 6)
    CURLE_COULDNT_RESOLVE_PROXY = _get_pycurl_errcode('E_COULDNT_RESOLVE_PROXY', 5)
    CURLE_GOT_NOTHING = _get_pycurl_errcode('E_GOT_NOTHING', 52)
    CURLE_PARTIAL_FILE = _get_pycurl_errcode('E_PARTIAL_FILE', 18)
    CURLE_SEND_ERROR = _get_pycurl_errcode('E_SEND_ERROR', 55)
    CURLE_SSL_CACERT = _get_pycurl_errcode('E_SSL_CACERT', 60)
    CURLE_SSL_CACERT_BADFILE = _get_pycurl_errcode('E_SSL_CACERT_BADFILE', 77)    


class CurlTransport(HTTPTransportBase):
    """
    An HTTP transportthat uses pycurl.

    Pycurl is recommanded when you want fast access to http resources.
    We have added some basic management of authentification and proxies,
    but in case you want something specific you should use urllib2 or 
    httplib2 http clients. Any patch is welcome though ;)


    Here is an example to use authentification with curl httpclient :
    
    .. code-block:: python

        httpclient = CurlTransport()
        httpclient.add_credentials("test", "test")        

    .. seealso::
        
        `Pycurl <http://pycurl.sourceforge.net>`_
    """

    def __init__(self, timeout=None, proxy_infos=None):
        """ Curl transport constructor

        :param timeout: int, timeout of request
        :param proxy_infos: dict, infos to connect via proxy:

        .. code-block:: python

            {
                'proxy_user': 'XXXXXXX',
                'proxy_password': 'XXXXXXX',
                'proxy_host': 'proxy',
                'proxy_port': 8080,
            }
        """
        HTTPTransportBase.__init__(self, proxy_infos=proxy_infos)

        # path to certificate file
        self.cabundle = None

        if pycurl is None:
            raise RuntimeError('Cannot find pycurl library')

        self.timeout = timeout
        
    def _parseHeaders(self, header_file):
        header_file.seek(0)
       
        # Remove the status line from the beginning of the input
        unused_http_status_line = header_file.readline()
        lines = [line.strip() for line in header_file]
        
        # and the blank line from the end
        empty_line = lines.pop()
        if empty_line:
            raise TransportError("No blank line at end")
       
        headers = {}
        for line in lines:
            if ":" in line:
                try:
                    name, value = line.split(':', 1)
                except ValueError:
                    raise TransportError(
                        "Malformed HTTP header line in response: %r" % (line,))

                value = value.strip()

                # HTTP headers are case-insensitive
                name = name.lower()
                headers[name] = value

        return headers


    def request(self, url, method='GET', body=None, headers=None):
        body = body or ""        
        headers = headers or {}
        headers.setdefault('User-Agent',
                           "%s %s" % (USER_AGENT, pycurl.version,))

        # by default turn off default pragma
        headers.setdefault('Cache-control', 'max-age=0')
        headers.setdefault('Pragma', 'no-cache')

        if method in 'PUT':
            headers.setdefault('Expect', '100-continue')

        # encode url
        url = iri2uri(to_bytestring(url))
        
        c = pycurl.Curl()
        try:
            # set curl options
            if self.timeout is not None:
                c.setopt(pycurl.TIMEOUT, self.timeout)
            else:
                c.setopt(pycurl.TIMEOUT, 20)

            data = StringIO.StringIO()
            header = StringIO.StringIO()
            c.setopt(pycurl.WRITEFUNCTION, data.write)
            c.setopt(pycurl.HEADERFUNCTION, header.write)
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.FOLLOWLOCATION, 1)
            c.setopt(pycurl.MAXREDIRS, 5)
            c.setopt(pycurl.NOSIGNAL, 1)

            if self.cabundle:
                c.setopt(pycurl.CAINFO, celf.cabundle)

            #set proxy
            if self.proxy_infos and self.proxy_infos.get('proxy_host', ''):
                c.setopt(pycurl.PROXYAUTH, pycurl.HTTPAUTH_ANY)
                c.setopt(pycurl.PROXY, self.proxy_infos.get('proxy_host'))
                
                proxy_port = self.proxy_infos.get('proxy_port', '')
                if proxy_port:
                    c.setopt(pycurl.PROXYPORT, str(proxy_port))

                user = self.proxy_infos.get('proxy_user', '')
                if user:
                    userpass = "%s:%s" % (user, self.proxy_infos.get('proxy_password', ''))
                    c.setopt(pycurl.PROXYUSERPWD, userpass)
            
            # authentification
            auth = self._get_credentials()
            user = auth.get('user', None)
            password = auth.get('password', None)
            if user is not None:
                c.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_ANY)
                userpass = user + ':'
                if password is not None: # '' is a valid password
                    userpass += password
                c.setopt(pycurl.USERPWD, userpass)
    
            # set method
            if method == "GET":
                c.setopt(pycurl.HTTPGET, 1)
            elif method == "HEAD":
                c.setopt(pycurl.HTTPGET, 1)
                c.setopt(pycurl.NOBODY, 1)
            elif method == "POST":
                c.setopt(pycurl.POST, 1)
            elif method == "PUT":
                c.setopt(pycurl.UPLOAD, 1)
            else:
                c.setopt(pycurl.CUSTOMREQUEST, method)

            if method in ('POST','PUT'):
                if hasattr(body, 'read'):
                    content_length = int(headers.pop('Content-Length',
                        0))
                    content = body
                else:
                    body = to_bytestring(body)
                    content = StringIO.StringIO(body)
                    if 'Content-Length' in headers:
                        del headers['Content-Length']
                    content_length = len(body)

                if method in ('POST'):
                    c.setopt(pycurl.POSTFIELDSIZE, content_length)
                else:
                    c.setopt(pycurl.INFILESIZE, content_length)
                c.setopt(pycurl.READFUNCTION, content.read)
            
            if headers:
                _normalize_headers(headers)

                c.setopt(pycurl.HTTPHEADER,
                        ["%s: %s" % pair for pair in sorted(headers.iteritems())])

                
            try:
                c.perform()
            except pycurl.error, e:
                if e[0] != CURLE_SEND_ERROR:
                    raise TransportError(e)
 
            response_headers = self._parseHeaders(header)
            code = c.getinfo(pycurl.RESPONSE_CODE)
            
            return self._make_response(final_url=url, status=code,
                    headers=response_headers, body=data.getvalue())
        finally:
            c.close()

    def _make_response(self, final_url=None, status=None, headers=None,
            body=None):
        infos = headers or {}
        infos.update({
            'status': status,
            'final_url': final_url
        })
        resp = HTTPResponse(infos)
        return resp, body 
    
class HTTPLib2Transport(HTTPTransportBase):
    """An http client that uses httplib2 for performing HTTP
    requests. This implementation supports HTTP caching.

    .. seealso::
        
        `Httplib2 <http://code.google.com/p/httplib2/>`_
    """

    def __init__(self, proxy_infos=None, http=None):
        """
        :param proxy_infos: dict, infos to connect via proxy:

        .. code-block:: python
    
            {
                'proxy_user': 'XXXXXXX',
                'proxy_password': 'XXXXXXX',
                'proxy_host': 'proxy',
                'proxy_port': 8080,
            }

        :param http: An httplib2.HTTP instance.


        """
        if httplib2 is None:
            raise RuntimeError('Cannot find httplib2 library. '
                               'See http://bitworking.org/projects/httplib2/')

        super(HTTPLib2Transport, self).__init__(proxy_infos=proxy_infos)
        
        _proxy_infos = None
        if proxy_infos and proxy_infos is not None:
            try:
                import socks
            except:
                print >>sys.stderr, "socks module isn't installed, you can't use proxy"
                socks = None

            if socks is not None:
                _proxy_infos = httplib2.ProxyInfo(
                        socks.PROXY_TYPE_HTTP,
                        proxy_infos.get('proxy_host'),
                        proxy_infos.get('proxy_port'),
                        proxy_infos.get('proxy_username'),
                        proxy_infos.get('proxy_password')
                )

        if http is None:
            http = httplib2.Http(proxy_info=_proxy_infos)
        else:
            if _proxy_infos is not None and \
                    not http.proxy_info and \
                    http.proxy_info is None:
                proxy_info = _proxy_infos
        self.http = http
        
        self.http.force_exception_to_status_code = False

    def request(self, url, method='GET', body=None, headers=None):
        headers = headers or {}
        body = body or ''
        
        content = ''
        if method in ('POST','PUT'):
            if hasattr(body, 'read'):
                content_length = int(headers.pop('Content-Length',
                    0))
                content = body.read()
            else:
                content = body
                if 'Content-Length' in headers:
                    del headers['Content-Length']
                content_length = len(body)

            headers.setdefault('Content-Length', str(content_length))

        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('URL is not a HTTP URL: %r' % (url,))

        headers.setdefault('User-Agent', USER_AGENT)
        
        httplib2_response, content = self.http.request(url,
                method=method, body=content, headers=headers)

        try:
            final_url = httplib2_response['content-location']
        except KeyError:
            final_url = url

        
        resp = HTTPResponse(httplib2_response)
        return resp, content

    def add_credentials(self, user, password):
        super(HTTPLib2Transport, self).add_credentials(user, password)
        self.http.add_credentials(user, password)
