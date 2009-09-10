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


# TODO: log error

import collections
import httplib
from Queue import Queue, Full, Empty
import socket
import threading
import time
import weakref

from restkit import errors

class ConnectionPool(object):
    def __init__(self, creator, recycle=60, pool_size=5, max_overflow=10, 
            timeout=60, use_threadlocal=True):
        self._creator = creator
        self._recycle = recycle
        self._pool_size = pool_size
        self._overflow = 0 - pool_size
        self._max_overflow = max_overflow
        self._use_threadlocal = use_threadlocal
        self._timeout = timeout
        self._pool = Queue(pool_size)
        self._threadconns = threading.local()
        self._overflow_lock = self._max_overflow > -1 and threading.Lock() or None
        
    def create_connection(self):
        if self._use_threadlocal and hasattr(self._threadconns, "current"):
            return self._threadconns.current
        return ConnectionRecord(self)
            
    def do_get(self):
        try:
            wait = self._max_overflow > -1 and self._overflow >= self._max_overflow
            return self._pool.get(wait, self._timeout)
        except Empty:
            if self._max_overflow > -1 and self._overflow >= self._max_overflow:
                if not wait:
                    return self.do_get()
                else:
                    raise errors.TimeoutError("Pool limit of size %d oveflow %d reached, connection timed out, timeout %d" % (self.current_size, self.max_size, self.timeout))
        
            if self._overflow_lock is not None:
                self._overflow_lock.acquire()
                
            if self._max_overflow > -1 and self._overflow >= self._max_overflow:
                if self._overflow_lock is not None:
                    self._overflow_lock.release()
                return self.do_get()
            try:
                con = self.create_connection()
                self._overflow += 1
            finally:
                if self._overflow_lock is not None:
                    self._overflow_lock.release()
                return con

    def size(self):
        return self._pool.maxsize
                
    def get(self):
        return self.do_get()
        
        
    def do_put(self, conn):
        try:
            self._pool.put(conn, False)
        except Full:
            if self._overflow_lock is None:
                self._overflow -= 1
            else:
                self._overflow_lock.acquire()
                try:
                    self._overflow -= 1
                finally:
                    self._overflow_lock.release()
                    
    def put(self, record):
        if self._use_threadlocal and hasattr(self._threadconns, "current"):
            del self._threadconns.current
        self.do_put(record)
        
        
        
class ConnectionRecord(object):
    """ Object to keep connection and its time
    for recycle """
    def __init__(self, pool):
        self.__pool = pool
        self.connection = self.__connect()
        
    def get_connection(self):
        """ get connection, 
        if it's invalidated create it or if 
        we have kept it too much time we recycle it
        """
        if self.connection is None:
            self.connection = self.__connect()
        elif (self.__pool._recycle > -1 and time.time() - self.starttime > self.__pool._recycle):
            self.__close()
            self.connection = self.__connect()
        return self.connection
        
    def close(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except:
                pass
        
    def invalidate(self):
        """ close a connection and invalidate it """
        self.__close()
        self.connection = None
        
    def __connect(self):
        """ connect """
        try:
            self.starttime = time.time()
            connection = self.__pool._creator()
            return connection
        except:
            pass
            
    def __close(self):
        """ close the connection """
        try:
            self.connection.close()
        except:
            pass
        

        
        