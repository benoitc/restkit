# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import socket
import sys

CHUNK_SIZE = (16 * 1024)
MAX_BODY = 1024 * 112
DNS_TIMEOUT = 60
 
_allowed_ssl_args = ('keyfile', 'certfile', 'server_side',
                    'cert_reqs', 'ssl_version', 'ca_certs', 
                    'do_handshake_on_connect', 'suppress_ragged_eofs')

def validate_ssl_args(ssl_args):
    for arg in ssl_args:
        if arg not in _allowed_ssl_args:
            raise TypeError('connect() got an unexpected keyword argument %r' % arg)   

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

# Check if running in Jython
if 'java' in sys.platform:
    from javax.net.ssl import TrustManager, X509TrustManager
    from jarray import array
    from javax.net.ssl import SSLContext
    class TrustAllX509TrustManager(X509TrustManager):
        '''Define a custom TrustManager which will blindly accept all certificates'''

        def checkClientTrusted(self, chain, auth):
            pass

        def checkServerTrusted(self, chain, auth):
            pass

        def getAcceptedIssuers(self):
            return None
    # Create a static reference to an SSLContext which will use
    # our custom TrustManager
    trust_managers = array([TrustAllX509TrustManager()], TrustManager)
    TRUST_ALL_CONTEXT = SSLContext.getInstance("SSL")
    TRUST_ALL_CONTEXT.init(None, trust_managers, None)
    # Keep a static reference to the JVM's default SSLContext for restoring
    # at a later time
    DEFAULT_CONTEXT = SSLContext.getDefault()
 
def trust_all_certificates(f):
    '''Decorator function that will make it so the context of the decorated method
    will run with our TrustManager that accepts all certificates'''
    def wrapped(*args, **kwargs):
        # Only do this if running under Jython
        if 'java' in sys.platform:
            from javax.net.ssl import SSLContext
            SSLContext.setDefault(TRUST_ALL_CONTEXT)
            try:
                res = f(*args, **kwargs)
                return res
            finally:
                SSLContext.setDefault(DEFAULT_CONTEXT)
        else:
            return f(*args, **kwargs)
    return wrapped

