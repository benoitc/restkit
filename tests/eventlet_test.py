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

import unittest
from eventlet.util import wrap_threading_local_with_coro_local
wrap_threading_local_with_coro_local()

from restkit.rest import Resource
from restkit.ext.eventlet_pool import ConnectionPool
from _server_test import HOST, PORT, run_server_test

from httpc_test import HTTPClientTestCase




class EventletTestCase(HTTPClientTestCase):
    def setUp(self):
        
        run_server_test()
        self.url = 'http://%s:%s' % (HOST, PORT)
        self.res = Resource(self.url, pool_class=ConnectionPool)

if __name__ == '__main__':
    from _server_test import run_server_test
    run_server_test()
    unittest.main()