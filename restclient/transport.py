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
import StringIO
import httplib
import re
import sys

import restclient

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

def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
   
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s


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
    return isinstance(_default_http, CurlHTTPTransport)

class HTTPError(Exception):
    """ raised when there is an HTTP error """

class HTTPResponse(dict):
    headers = None
    status = 200
    final_url = None
    body = None

    def __init__(self, final_url=None, status=None, headers=None,
            body=None):
        self.final_url = final_url
        self.status = status
        self.headers = headers
        self.body = body

    def __repr__(self):
        return "<%s status %s for %s>" % (self.__class__.__name__,
                                          self.status,
                                          self.final_url)

class HTTPTransportBase(object):
    """ Interface for HTTP clients """

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

    def __init__(self, timeout=None):
        HTTPTransportBase.__init__(self)
        self._credentials = {}

        # path to certificate file
        self.cabundle = None

        if pycurl is None:
            raise RuntimeError('Cannot find pycurl library')

        self.timeout = timeout
            

    def _parseHeaders(self, status_and_headers):
        status_and_headers.seek(0)

        # Ignore status line
        status_and_headers.readline()
        msg = httplib.HTTPMessage(status_and_headers)
        return dict(msg.items())

    def request(self, url, method='GET', body=None, headers=None):
        put = method in ('PUT')
        body = body or ""        
        headers = headers or {}
        headers.setdefault('User-Agent',
                           "%s %s" % (USER_AGENT, pycurl.version,))

        # turn off default pragma provided by Curl
        headers.update({
            'Cache-control': 'max-age=0',
            'Pragma': 'no-cache'
        })

        if put:
            headers.setdefault('Expect', '100-continue')

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
            c.setopt(pycurl.URL , smart_str(url))
            c.setopt(pycurl.FOLLOWLOCATION, 1)
            c.setopt(pycurl.MAXREDIRS, 5)

            if self.cabundle:
                c.setopt(pycurl.CAINFO, celf.cabundle)

            auth = self._get_credentials()
            user = auth.get('user', None)
            password = auth.get('password', None)
            if user is not None:
                # accept any auth methode
                c.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_ANY)
                c.setopt(pycurl.PROXYAUTH, pycurl.HTTPAUTH_ANY)
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
                    content = StringIO.StringIO(body)
                    if 'Content-Length' in headers:
                        del headers['Content-Length']
                    content_length = len(body)

                if put:
                    c.setopt(pycurl.INFILESIZE, content_length)
                if method in ('POST'):
                    c.setopt(pycurl.POSTFIELDSIZE, content_length)
                c.setopt(pycurl.READFUNCTION, content.read)
            
            if headers:
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

    def add_credentials(self, user, password):
        self._credentials = {
                "user": user,
                "password": password
        }

    def _get_credentials(self):
        return self._credentials


    def _make_response(self, final_url=None, status=None, headers=None,
            body=None):
        resp = HTTPResponse()
        resp.headers = headers or {}
        resp.status = status
        resp.final_url = final_url
        resp.body = body
        return resp, body 
    
class HTTPLib2Transport(HTTPTransportBase):
    """An http client that uses httplib2 for performing HTTP
    requests. This implementation supports HTTP caching.

    .. seealso::
        
        `Httplib2 <http://code.google.com/p/httplib2/>`_
    """

    def __init__(self, http=None):
        """@param http: An httplib2.HTTP instance.
        """
        if httplib2 is None:
            raise RuntimeError('Cannot find httplib2 library. '
                               'See http://bitworking.org/projects/httplib2/')

        super(HTTPLib2Transport, self).__init__()
        
        if http is None:
            http = httplib2.Http()

        self.http = http
        self.http.force_exception_to_status_code = False

    def request(self, url, method='GET', body=None, headers=None):
        headers = headers or {}
      
        content = ''
        if method in ['POST', 'PUT']:
            body = body or ''
            if hasattr(body, 'read'): # httplib2 don't suppport file read
                content = body.read()
            else:
                content = body
                headers.setdefault('Content-Length', str(len(body))) 

        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('URL is not a HTTP URL: %r' % (url,))

        headers.setdefault('User-Agent', USER_AGENT)
        
        httplib2_response, content = self.http.request(url,
                method=method, body=content, headers=headers)


        try:
            final_url = httplib2_response['content-location']
        except KeyError:
            final_url = url

        resp = HTTPResponse()
        resp.headers = dict(httplib2_response.items())
        resp.status = int(httplib2_response.status)
        resp.final_url = final_url
        resp.body = content

        return resp, content
