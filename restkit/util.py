# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import errno
import os
import select
import socket
import time
import urllib

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
        
if not hasattr(socket, '_GLOBAL_DEFAULT_TIMEOUT'): # python < 2.6
    _GLOBAL_DEFAULT_TIMEOUT = object()

def connect(address, timeout=_GLOBAL_DEFAULT_TIMEOUT, ssl=False, 
        key_file=None, cert_file=None):
    msg = "getaddrinfo returns an empty list"
    host, port = address
    for res in socket.getaddrinfo(host, port, 0, SOCK_STREAM):
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

def to_bytestring(s):
    if not isinstance(s, basestring):
        raise TypeError("value should be a str or unicode")

    if isinstance(s, unicode):
        return s.encode('utf-8')
    return s
    
def url_quote(s, charset='utf-8', safe='/:'):
    """URL encode a single string with a given encoding."""
    if isinstance(s, unicode):
        s = s.encode(charset)
    elif not isinstance(s, str):
        s = str(s)
    return urllib.quote(s, safe=safe)

def url_encode(obj, charset="utf8", encode_keys=False):
    if isinstance(obj, dict):
        items = []
        for k, v in obj.iteritems():
            if not isinstance(v, (tuple, list)):
                v = [v]
            items.append((k, v))
    else:
        items = obj or ()

    tmp = []
    for key, values in items:
        if encode_keys and isinstance(key, unicode):
            key = key.encode(charset)
        else:
            key = str(key)

        for value in values:
            if value is None:
                continue
            elif isinstance(value, unicode):
                value = value.encode(charset)
            else:
                value = str(value)
        tmp.append('%s=%s' % (urllib.quote(key),
            urllib.quote_plus(value)))

    return '&'.join(tmp)