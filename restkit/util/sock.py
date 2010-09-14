# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import socket

CHUNK_SIZE = (16 * 1024)
MAX_BODY = 1024 * 112

try:
    import ssl # python 2.6
    have_ssl = True
except ImportError:
    have_ssl = False
        
if not hasattr(socket, '_GLOBAL_DEFAULT_TIMEOUT'): # python < 2.6
    _GLOBAL_DEFAULT_TIMEOUT = object()
else:
    _GLOBAL_DEFAULT_TIMEOUT = socket._GLOBAL_DEFAULT_TIMEOUT
    
_allowed_ssl_args = ('keyfile', 'certfile', 'server_side',
                    'cert_reqs', 'ssl_version', 'ca_certs', 
                    'do_handshake_on_connect', 'suppress_ragged_eofs')

def connect(address, is_ssl, timeout=_GLOBAL_DEFAULT_TIMEOUT, **ssl_args):
    ssl_args = ssl_args or {}
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
            if is_ssl:
                if not have_ssl:
                    raise ValueError("https isn't supported.  On python 2.5x,"
                                + " https support requires ssl module "
                                + "(http://pypi.python.org/pypi/ssl) "
                                + "to be intalled.")
                                
                for arg in ssl_args:
                    if arg not in _allowed_ssl_args:
                        raise TypeError('connect() got an unexpected keyword argument %r' % arg)   
                return ssl.wrap_socket(sock, **ssl_args)
            return sock
        except socket.error, msg:
            if sock is not None:
                sock.close()
    raise socket.error, msg
    
def close(skt):
    if not skt or not hasattr(skt, "close"): return
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
