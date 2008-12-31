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
import urllib2

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


def createHTTPClient():
    """Create default HTTP client instance
    prefers Curl to urllib"""

    if pycurl is None:
        http = Urllib2HTTPClient()
    else:
        http = CurlHTTPClient()

    return http

def getDefaultHTTPClient():
    """ Return the default http client instance instance
    if no client has been set, it will create a default client.

    :return: the default client
    """

    global _default_http

    if _default_http is None:
        setDefaultHTTPClient(createHTTPClient())

    return _default_http

def setDefaultHTTPClient(httpclient):
    """ set default httpClient 
    :param http: RestClient
    """
    global _default_http

    _default_http = httpclient

def useCurl():
    global _default_http
    return isinstance(_default_http, CurlHTTPClient)

class HTTPError(Exception):
    """ raised when there is an HTTP error """

class HTTPResponse(dict):
    headers = None
    status = 200
    final_url = None
    
    def __init__(self, final_url=None, status=None, headers=None,
            body=None):
        self.final_url = final_url
        self.status_code = status
        self.headers = headers
        self.body = body

    def __repr__(self):
        return "<%s status %s for %s>" % (self.__class__.__name__,
                                          self.status,
                                          self.final_url)

class HTTPClient(object):
    """ Interface for HTTP clients """

    def __init__(self):
        self._credentials = {}

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

class CustomRequest(urllib2.Request):
    _method = None

    def __init__(self, url, data=None, headers={},
                 origin_req_host=None, unverifiable=False, method=None):
        urllib2.Request.__init__(self, url, data=data, headers=headers,
                 origin_req_host=origin_req_host, unverifiable=unverifiable)

        if method is not None:
            self._method = method

    def get_method(self):
        if self._method is not None:
            return self._method

        if self.has_data():
            return "POST"
        else:
            return "GET"


USE_WWW_AUTH_STRICT_PARSING = 0

# In regex below:
#    [^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+             matches a "token" as defined by HTTP
#    "(?:[^\0-\x08\x0A-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?"    matches a "quoted-string" as defined by HTTP, when LWS have already been replaced by a single space
# Actually, as an auth-param value can be either a token or a quoted-string, they are combined in a single pattern which matches both:
#    \"?((?<=\")(?:[^\0-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?(?=\")|(?<!\")[^\0-\x08\x0A-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+(?!\"))\"?
WWW_AUTH_STRICT = re.compile(r"^(?:\s*(?:,\s*)?([^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+)\s*=\s*\"?((?<=\")(?:[^\0-\x08\x0A-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?(?=\")|(?<!\")[^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+(?!\"))\"?)(.*)$")
WWW_AUTH_RELAXED = re.compile(r"^(?:\s*(?:,\s*)?([^ \t\r\n=]+)\s*=\s*\"?((?<=\")(?:[^\\\"]|\\.)*?(?=\")|(?<!\")[^ \t\r\n,]+(?!\"))\"?)(.*)$")
UNQUOTE_PAIRS = re.compile(r'\\(.)')
def _parse_www_authenticate(headers):
    """Returns a dictionary of dictionaries, one dict
    per auth_scheme.
    
    from httplib2
    """
    retval = {}
    authenticate = headers['www-authenticate'].strip()
    www_auth = USE_WWW_AUTH_STRICT_PARSING and WWW_AUTH_STRICT or WWW_AUTH_RELAXED
    while authenticate:
        (auth_scheme, the_rest) = authenticate.split(" ", 1)
        # Now loop over all the key value pairs that come after the scheme, 
        # being careful not to roll into the next scheme
        match = www_auth.search(the_rest)
        auth_params = {}
        while match:
            if match and len(match.groups()) == 3:
                (key, value, the_rest) = match.groups()
                auth_params[key.lower()] = UNQUOTE_PAIRS.sub(r'\1', value) # '\\'.join([x.replace('\\', '') for x in value.split('\\\\')])
            match = www_auth.search(the_rest)
        retval[auth_scheme.lower()] = auth_params
        authenticate = the_rest.strip()
    return retval

class Urllib2HTTPClient(HTTPClient):
    """ HTTP Client that use urllib2.
    This module is included in python so i mean that you don't need any
    dependancy to run this client and restclient.

    urllib2 is very powerfull and you can use many handlers to manage
    authentification and proxies.

    .. seealso::
        
        `Urllib2 <http://docs.python.org/library/urllib2.html>`_
    
    """

    def __init__(self):
        """ Constructor for Urllib2HTTPClient """
        HTTPClient.__init__(self)

    def _request(self, url, method, body, headers):
        req = CustomRequest(url=url, data=body, method=method)
        
        for key, value in headers.items():
            req.add_header(key, value)
        
        try:
            f = urllib2.urlopen(req)
            try:
                return self._make_response(f)
            finally:
                f.close()
        except urllib2.HTTPError, e:
            try:
                return self._make_response(e)
            finally:
                e.close()

        
    def request(self, url, method='GET', body=None, headers=None):
        headers = headers or {}
        body = body or ''
        
        # reset auth
        urllib2.install_opener(urllib2.build_opener())

        headers.setdefault('User-Agent',
            "%s Python-urllib/%s" % (USER_AGENT, urllib2.__version__,))

        resp, content = self._request(url, method, body, headers)
        if resp.status == 401:
            auth = self._get_credentials()
            user = auth.get('user', None)
            password = auth.get('password', None)
            if user is not None:
                challenges =  _parse_www_authenticate(resp.headers)      
                auth_handler = None
                if challenges.has_key('basic'):
                    auth_handler = urllib2.HTTPBasicAuthHandler()
                    auth_handler.add_password(challenges['basic']['realm'], 
                            url, user, password)
                elif challenges.has_key('digest'):
                    auth_handler = urllib2.HTTPDigestAuthHandler()
                    auth_handler.add_password(challenge['digest']['realm'], 
                            url, user, password)
                   
                if auth_handler is not None:
                    opener = urllib2.build_opener(auth_handler)
                    urllib2.install_opener(opener)
                    resp, content = self._request(url, method, body, headers)
        return resp, content


    def _make_response(self, response):
        resp = HTTPResponse()
        resp.final_url = response.geturl()
        resp.headers = dict(response.info().items())
        resp.body = response.read()

        if hasattr(response, 'code'):
            resp.status = response.code
        else:
            resp.status = 200

        return resp, resp.body

class CurlHTTPClient(HTTPClient):
    """
    An HTTPClient that uses pycurl.

    Pycurl is recommanded when you want fast access to http resources.
    We have added some basic management of authentification and proxies,
    but in case you want something specific you should use urllib2 or 
    httplib2 http clients. Any patch is welcome though ;)


    Here is an example to use authentification with curl httpclient :
    
    .. code-block:: python

        httpclient = CurlHTTPClient()
        httpclient.add_credentials("test", "test")        

    .. seealso::
        
        `Pycurl <http://pycurl.sourceforge.net>`_
    """

    def __init__(self, timeout=None):
        HTTPClient.__init__(self)
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
        
        if method in ['POST', 'PUT']:
            body = body or ''
            headers.setdefault('Content-Length', str(len(body))) 


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
            #.setopt(pycurl.VERBOSE, 1)

            if headers:
                c.setopt(pycurl.HTTPHEADER,
                        ["%s: %s" % pair for pair in sorted(headers.iteritems())])


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
                if put:
                    c.setopt(pycurl.INFILESIZE, len(body))
                if method in ('POST'):
                    c.setopt(pycurl.POSTFIELDSIZE, len(body))
                s = StringIO.StringIO(body)
                c.setopt(pycurl.READFUNCTION, s.read)
            
            try:
                c.perform()
            except pycurl.error, e:
                errno, message = e
                return self._make_response(final_url=url, status=errno,
                        body=message)

            response_headers = self._parseHeaders(header)
            code = c.getinfo(pycurl.RESPONSE_CODE)
            
            return self._make_response(final_url=url, status=code,
                    headers=response_headers, body=data.getvalue())
        finally:
            c.close()

    def _make_response(self, final_url=None, status=None, headers=None,
            body=None):
        resp = HTTPResponse()
        resp.headers = headers
        resp.status = status
        resp.final_url = final_url
        resp.body = body
        return resp, body 
    
class HTTPLib2HTTPClient(HTTPClient):
    """An http client that uses httplib2 for performing HTTP
    requests. This implementation supports HTTP caching.

    .. seealso::
        
        `Httplib2 <http://code.google.com/p/httplib2/>`_
    """

    def __init__(self, cache=None):
        """@param cache: An object suitable for use as an C{httplib2}
            cache. If a string is passed, it is assumed to be a
            directory name.
        """
        if httplib2 is None:
            raise RuntimeError('Cannot find httplib2 library. '
                               'See http://bitworking.org/projects/httplib2/')

        super(HTTPLib2HTTPClient, self).__init__()
        
        self.http = httplib2.Http(cache)
        self.http.force_exception_to_status_code = False

    def request(self, url, method='GET', body=None, headers=None):
        headers = headers or {}
       
        if method in ['POST', 'PUT']:
            body = body or ''
            headers.setdefault('Content-Length', str(len(body))) 

        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('URL is not a HTTP URL: %r' % (url,))

        headers.setdefault('User-Agent', USER_AGENT)
        
        self.http.clear_credentials()

        auth = self._get_credentials()
        user = auth.get('user', None)
        password = auth.get('password', None)
        if user is not None:
            self.http.add_credentials(user, password)

        httplib2_response, content = self.http.request(url,
                method=method, body=body, headers=headers)


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
