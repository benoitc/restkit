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

"""
curl transport
"""

import re
import StringIO
import sys


import restclient
from restclient.errors import TransportError
from restclient.transport.base import *
from restclient.utils import to_bytestring, iri2uri

try:
    import pycurl
except ImportError:
    pycurl = None
    
NORMALIZE_SPACE = re.compile(r'(?:\r\n)?[ \t]+')
def _normalize_headers(headers):
    return dict([ (key.lower(), NORMALIZE_SPACE.sub(value, ' ').strip())  for (key, value) in headers.iteritems()])


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

        if method == 'PUT':
            headers.setdefault('Expect', '100-continue')

        # encode url
        origin_url = to_bytestring(url)
        url = iri2uri(origin_url)

        c = pycurl.Curl()
        try:
            # set curl options
            if self.timeout is not None:
                c.setopt(pycurl.TIMEOUT, self.timeout)
            else: # no timeout by default
                c.setopt(pycurl.TIMEOUT, 0)

            data = StringIO.StringIO()
            header = StringIO.StringIO()
            c.setopt(pycurl.WRITEFUNCTION, data.write)
            c.setopt(pycurl.HEADERFUNCTION, header.write)
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.FOLLOWLOCATION, 1)
            c.setopt(pycurl.MAXREDIRS, 5)
            c.setopt(pycurl.NOSIGNAL, 1)
            if restclient.debuglevel > 0:
                 c.setopt(pycurl.VERBOSE, 1)
                 
            # automatic decompression
            c.setopt(pycurl.ENCODING, 'gzip,deflate')

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

                if method == 'POST':
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
                    if restclient.debuglevel > 0:
                        print >>sys.stderr, str(e)
                    raise TransportError(e)

            response_headers = self._parseHeaders(header)
            code = c.getinfo(pycurl.RESPONSE_CODE)
            return self._make_response(final_url=url, origin_url=origin_url,
                    status=code, headers=response_headers, body=data.getvalue())
        finally:
            c.close()

    def _make_response(self, final_url=None, origin_url=None, status=None, 
            headers=None, body=None):
        infos = headers or {}    
        final_url = infos.get('location', final_url)
        infos.update({
            'status': status,
            'final_url': final_url,
            'origin_url': origin_url
        })
        resp = HTTPResponse(infos)
        return resp, body