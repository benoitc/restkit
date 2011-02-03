# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

from collections import deque
import logging
import signal
import socket
import threading
import time

from ..sock import close

log = logging.getLogger(__name__)

class ConnectionReaper(threading.Thread):
    """ connection reaper thread. Open a thread that will murder iddle
    connections after a delay """

    running = False

    def __init__(self, manager, delay=150):
        self.manager = manager
        self.delay = delay
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        self.running = True
        while True:
            time.sleep(self.delay)
            self.manager.murder_connections()

    def ensure_started(self):
        if not self.running and not self.isAlive():
            self.start()

class Manager(object):
    """ Connection mager, it keeps a pool of opened connections and reap
    them after a delay if reap_connection is True. By default a thread
    is used to reap connections, but it can be replaced with signaling
    if needed. In this case a signal will be send to the manager after a
    delay. Be aware that using signaling isn't thread-safe and works
    only on UNIX or UNIX like."""

    def __init__(self, max_conn=10, timeout=150,
            reap_connections=True, with_signaling=False):
        self.max_conn = max_conn
        self.timeout = timeout
        self.reap_connections = reap_connections
        self.with_signaling = with_signaling

        self.sockets = dict()
        self.active_sockets = dict()
        self.connections_count = dict()
        self._lock = self.get_lock()

        self._reaper = None

        if reap_connections and timeout is not None:
            self.start()

    def get_lock(self):
        return threading.RLock()

    def murder_connections(self, *args):
        self._lock.acquire()
        log.debug("murder connections")
        try:
            active_sockets = self.active_sockets.copy()
            for fno, (sock, t0, k) in active_sockets.items():
                diff = time.time() - t0
                if diff <= self.timeout:
                    continue
                close(sock)
                del self.active_sockets[fno]
                self.connections_count[k] -= 1
        finally:
            self._lock.release()

    def close_connections(self):
        self._lock.acquire()
        try:
            active_sockets = self.active_sockets.copy()

            for fno, (sock, t0) in active_sockets.items():
                close(sock)
                del self.active_sockets[fno]
        finally:
            self._lock.release()

    def start(self):
        if self.with_signaling:
            signal.signal(signal.SIGALRM, self.murder_connections)
            signal.alarm(self.timeout)
        else:
            self._reaper = ConnectionReaper(self, delay=self.timeout)
            self._reaper.ensure_started()

    def all_connections_count(self):
        """ return all counts per address registered. """
        return self.connections_count.items()

    def connection_count(self, addr, ssl):
        """ get connections count for an address """
        self._lock.acquire()
        try:
            return self.connections_count[(addr, ssl)]
        finally:
            self._lock.release()

        return self.connections_count[(addr, ssl)]

    def find_socket(self, addr, ssl=False):
        """ find a socket from a its address in the pool and return if
        there is one available, else, return None """

        self._lock.acquire()
        try:
            key = (addr, ssl)
            log.debug("key %s" % str(key))
            try:
                socks = self.sockets[key]
                while True:
                    fno, sck = socks.pop()
                    if fno in self.active_sockets:
                        del self.active_sockets[fno]
                        break
                self.sockets[key] = socks
                self.connections_count[key] -= 1
                log.debug("fetch sock from pool")
                return sck
            except (IndexError, KeyError,):
                return None
        finally:
            self._lock.release()

    def store_socket(self, sck, addr, ssl=False):
        """ store a socket in the pool to reuse it across threads """

        if self._reaper is not None:
            self._reaper.ensure_started()

        self._lock.acquire()
        try:
            key = (addr, ssl)
            try:
                socks = self.sockets[key]
            except KeyError:
                socks = deque()

            if len(socks) < self.max_conn:
                # add connection to the pool
                try:
                    fno = sck.fileno() 
                except (socket.error, AttributeError,):
                    # socket has been closed
                    return

                self.active_sockets[fno] = (sck, time.time(), key)

                socks.appendleft((fno, sck))
                self.sockets[key] = socks
               
                log.debug("insert sock in pool")
                try:
                    self.connections_count[key] += 1
                except KeyError:
                    self.connections_count[key] = 1 

            else:
                # close connection if we have enough connections in the
                # pool.
                close(sck)
        finally:
            self._lock.release()
