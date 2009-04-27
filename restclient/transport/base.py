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
import sys

import restclient

USER_AGENT = "py-restclient/%s (%s)" % (restclient.__version__, sys.platform)

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
