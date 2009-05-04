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

import restclient
from restclient.errors import InvalidUrl
from restclient.transport.base import *

try:
    import httplib2
except ImportError:
    httplib2 = None
    
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
        
        # set debug level
        httplib2.debuglevel = restclient.debuglevel
        
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
            error = 'URL is not a HTTP URL: %r' % (url,)
            if restclient.debuglevel > 0:
                print >>sys.stderr, str(error)
            raise InvalidUrl(error)

        headers.setdefault('User-Agent', USER_AGENT)
        
        httplib2_response, content = self.http.request(url,
                method=method, body=content, headers=headers)

        try:
            final_url = httplib2_response['content-location']
        except KeyError:
            final_url = url
            
        httplib2_response['final_url'] = final_url
        httplib2_response['origin_url'] = url
        resp = HTTPResponse(httplib2_response)
        return resp, content

    def add_credentials(self, user, password):
        super(HTTPLib2Transport, self).add_credentials(user, password)
        self.http.add_credentials(user, password)
