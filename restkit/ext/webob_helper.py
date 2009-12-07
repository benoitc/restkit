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

import restkit.errors
import webob.exc

class WebobResourceError(webob.exc.WSGIHTTPException):

    def __init__(self, msg=None, http_code=None, response=None):
        webob.exc.WSGIHTTPException.__init__(self)
        
        http_code = http_code or 500
        klass = webob.exc.status_map[http_code]
        self.code = http_code
        self.title = klass.title
        self.status = '%s %s' % (self.code, self.title)
        self.explanation = msg
        self.response = response
        # default params
        self.msg = msg

    def _status_int__get(self):
        """
        The status as an integer
        """
        return int(self.status.split()[0])
    def _status_int__set(self, value):
        self.status = value
    status_int = property(_status_int__get, _status_int__set, doc=_status_int__get.__doc__)
    
    status_code = restkit.errors.deprecated_property(
        status_int, 'status_code', 'use .status_int instead',
        warning=False)

    def _get_message(self):
        return self.explanation
    def _set_message(self, msg):
        self.explanation = msg or ''
    message = property(_get_message, _set_message)

webob_exceptions = False
def wrap_exceptions():
    """ wrap restkit exception to return WebBob exceptions"""
    global webob_exceptions
    if webob_exceptions: return
    restkit.errors.ResourceError = WebobResourceError
    webob_exceptions = True
    