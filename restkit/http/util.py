# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import errno
import os
import select
import socket
import time

CHUNK_SIZE = (16 * 1024)
MAX_BODY = 1024 * (80 + 32)

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None,
             'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
             
try:
    import ssl # python 2.6
    _ssl_wrap_socket = ssl.wrap_socket
except ImportError:
    def _ssl_wrap_socket(sock, key_file, cert_file):
        ssl_sock = socket.ssl(sock, key_file, cert_file)
        return ssl_sock
        
if hasattr(socket, 'create_connection'): # python 2.6
    _create_connection = socket.create_connection
else:
    # backport from python 2.6
    _GLOBAL_DEFAULT_TIMEOUT = object()
    def _create_connection(address, timeout=_GLOBAL_DEFAULT_TIMEOUT):
        msg = "getaddrinfo returns an empty list"
        host, port = address
        for res in getaddrinfo(host, port, 0, SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket(af, socktype, proto)
                if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                    sock.settimeout(timeout)
                sock.connect(sa)
                return sock

            except error, msg:
                if sock is not None:
                    sock.close()

        raise error, msg

def read_partial(sock, length):
    while True:
        try:
            ret = select.select([sock.fileno()], [], [], 0)
            if ret[0]: break
        except select.error, e:
            if e[0] == errno.EINTR:
                continue
            raise
    data = sock.recv(length)
    return data
    
def close(sock):
    try:
        sock.close()
    except socket.error:
        pass
  

def write(sock, data):
    buf = ""
    buf += data
    i = 0
    while buf:
        try:
            bytes = sock.send(buf)
            if bytes < len(buf):
                buf = buf[bytes:]
                continue
            return len(data)
        except socket.error, e:
            if e[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                break
            raise
        i += 1
        
def write_nonblock(sock, data):
    timeout = sock.gettimeout()
    if timeout != 0.0:
        try:
            sock.setblocking(0)
            return write(sock, data)
        finally:
            sock.setblocking(1)
    else:
        return write(sock, data)
    
def writelines(sock, lines):
    for line in list(lines):
        write(sock, line)
        
def writefile(sock, data):
    if hasattr(data, 'seek'):
        data.seek(0)
        
    while True:
        binarydata = data.read(CHUNK_SIZE)
        if binarydata == '': break
        write(data)
        
def normalize_name(name):
    return  "-".join([w.lower().capitalize() for w in name.split("-")])
    
def http_date(timestamp=None):
    """Return the current date and time formatted for a message header."""
    if timestamp is None:
        timestamp = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
            weekdayname[wd],
            day, monthname[month], year,
            hh, mm, ss)
    return s