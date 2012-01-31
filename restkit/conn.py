# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import logging
import select
import socket
import ssl
import time

from socketpool import Connector

CHUNK_SIZE = 16 * 1024
MAX_BODY = 1024 * 112
DNS_TIMEOUT = 60


class Connection(Connector):

    def __init__(self, host, port, pool=None, is_ssl=False,
            extra_headers=[], backend_mod=None, **ssl_args):
        self._s = backend_mod.Socket(socket.AF_INET, socket.SOCK_STREAM)

        self._s.connect((host, port))

        if is_ssl:
            self._s = ssl.wrap_socket(self._s, **ssl_args)

        self.pool = pool
        self.extra_headers = extra_headers
        self.is_ssl = is_ssl
        self.backend_mod = backend_mod
        self.host = host
        self.port = port
        self._connected = True
        self._life = time.time()
        self._released = False

    def matches(self, **match_options):
        target_host = match_options.get('host')
        target_port = match_options.get('port')
        return target_host == self.host and target_port == self.port

    def is_connected(self):
        if self._connected:
            try:
                r, _, _ = self.backend_mod.Select([self._s], [], [], 0.0)
                if not r:
                    return True
            except (ValueError, select.error,):
                return False
            self.close()
        return False

    def handle_exception(self, exception):
        raise

    def get_lifetime(self):
        return self._life

    def invalidate(self):
        self.close()
        self._connected = False
        self._life = -1

    def release(self, should_close=False):
        if self._released:
            return

        self._released = True
        if should_close:
            self.close()
        else:
            self.pool.release_connection(self)

    def close(self):
        if not self._s or not hasattr(self._s, "close"):
            return
        try:
            self._s.close()
        except:
            pass

    def socket(self):
        return self._s

    def send_chunk(self, data):
        chunk = "".join(("%X\r\n" % len(data), data, "\r\n"))
        self._s.sendall(chunk)

    def send(self, data, chunked=False):
        if chunked:
            return self.send_chunk(data)

        return self._s.sendall(data)

    def sendlines(self, lines, chunked=False):
        for line in list(lines):
            self.send(line, chunked=chunked)


    # TODO: add support for sendfile api
    def sendfile(self, data, chunked=False):
        """ send a data from a FileObject """

        if hasattr(data, 'seek'):
            data.seek(0)

        while True:
            binarydata = data.read(CHUNK_SIZE)
            if binarydata == '':
                break
            self.send(binarydata, chunked=chunked)


    def recv(self, size=1024):
        return self._s.recv(size)
