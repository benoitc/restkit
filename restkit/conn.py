# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import logging

from restkit import sock

log = logging.getLogger(__name__)

class Connection(object):

    def __init__(self, sck, manager, addr, ssl=False,
            extra_headers=None):
        self._sock = sck
        self.manager = manager
        self.addr = addr
        self.ssl = ssl
        self.extra_headers = extra_headers
        

    def release(self, should_close=False):
        if should_close:
            self.close() 
        else:
            if log.isEnabledFor(logging.DEBUG):
                log.debug("release connection")
            self.manager.store_socket(self._sock, self.addr, self.ssl)

    def close(self):
        if log.isEnabledFor(logging.DEBUG):
            log.debug("close connection")
        sock.close(self._sock)

    def socket(self):
        return self._sock


