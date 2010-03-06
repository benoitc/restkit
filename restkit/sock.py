# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import socket

CHUNK_SIZE = (16 * 1024)
MAX_BODY = 1024 * 112

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
    
def close(skt):
    if not skt: return
    try:
        skt.close()
    except socket.error:
        pass  
        
def send_chunk(sock, data):
    chunk = "".join(("%X\r\n" % len(data), data, "\r\n"))
    sock.sendall(chunk)

def send(sock, data, chunked=False):
    if chunked:
        return send_chunk(sock, data)
    sock.sendall(data)
        
def send_nonblock(sock, data, chunked=False):
    timeout = sock.gettimeout()
    if timeout != 0.0:
        try:
            sock.setblocking(0)
            return send(sock, data, chunked)
        finally:
            sock.setblocking(1)
    else:
        return send(sock, data, chunked)
    
def sendlines(sock, lines, chunked=False):
    for line in list(lines):
        send(sock, line, chunked)
        
def sendfile(sock, data, chunked=False):
    if hasattr(data, 'seek'):
        data.seek(0)
        
    while True:
        binarydata = data.read(CHUNK_SIZE)
        if binarydata == '': break
        send(sock, binarydata, chunked)