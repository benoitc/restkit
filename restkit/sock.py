# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import errno
import os
import select
import socket

CHUNK_SIZE = (16 * 1024)
MAX_BODY = 1024 * (80 + 32)

try:
    import ssl # python 2.6
    _ssl_wrap_socket = ssl.wrap_socket
except ImportError:
    def _ssl_wrap_socket(sock, key_file, cert_file):
        ssl_sock = socket.ssl(sock, key_file, cert_file)
        return ssl_sock
        
if not hasattr(socket, '_GLOBAL_DEFAULT_TIMEOUT'): # python < 2.6
    _GLOBAL_DEFAULT_TIMEOUT = object()
else:
    _GLOBAL_DEFAULT_TIMEOUT = socket._GLOBAL_DEFAULT_TIMEOUT

def connect(address, timeout=_GLOBAL_DEFAULT_TIMEOUT, ssl=False, 
        key_file=None, cert_file=None):
    msg = "getaddrinfo returns an empty list"
    host, port = address
    for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            sock.connect(sa)
            if ssl:
                sock = _ssl_wrap_socket(sock, key_file, cert_file)
            return sock
        except socket.error, msg:
            if sock is not None:
                sock.close()
    raise socket.error, msg
    
        
def recv(sock, length):
    return sock.recv(length)
    
    while True:
        try:
            ret = select.select([sock.fileno()], [], [], 0)
            if ret[0]:
                return sock.recv(length)
        except select.error, e:
            if e[0] == errno.EINTR:
                continue
            raise
    return ''
  
def close(sock):
    try:
        sock.close()
    except socket.error:
        pass  

def send(sock, data):
    try:
        sock.sendall(data)
    except socket.error, e:
        if e[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
            pass
        raise
        
def send_nonblock(sock, data):
    timeout = sock.gettimeout()
    if timeout != 0.0:
        try:
            sock.setblocking(0)
            return send(sock, data)
        finally:
            sock.setblocking(1)
    else:
        return send(sock, data)
    
def sendlines(sock, lines):
    for line in list(lines):
        send(sock, line)
        
def sendfile(sock, data):
    if hasattr(data, 'seek'):
        data.seek(0)
        
    while True:
        binarydata = data.read(CHUNK_SIZE)
        if binarydata == '': break
        send(sock, binarydata)