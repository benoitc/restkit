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

from restclient.transport.base import HTTPResponse, HTTPTransportBase, USER_AGENT
from restclient.transport._httplib2 import HTTPLib2Transport, httplib2
from restclient.transport._curl import CurlTransport, pycurl

__all__ = [
    'HTTPResponse', 
    'HTTPTransportBase', 
    'USER_AGENT',
    'HTTPLib2Transport',
    'CurlTransport',
    'createHTTPTransport',
    'setDefaultHTTPTransport',
    'useCurl']

_default_http = None


def createHTTPTransport():
    """Create default HTTP client instance
    prefers Curl to urllib"""
    if pycurl is not None:
        http = CurlTransport()
    elif httplib2 is not None:
        http = HTTPLib2Transport()
    else:
        raise RuntimeError("httplib2 or curl are missing")
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
