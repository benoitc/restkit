# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import time
import urllib

from restkit.errors import InvalidUrl

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None,
             'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
             
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

def parse_netloc(uri):
    host = uri.netloc
    port = None
    i = host.rfind(':')
    j = host.rfind(']')         # ipv6 addresses have [...]
    if i > j:
        try:
            port = int(host[i+1:])
        except ValueError:
            raise InvalidUrl("nonnumeric port: '%s'" % host[i+1:])
        host = host[:i]
    else:
        # default port
        if uri.scheme == "https":
            port = 443
        else:
            port = 80
            
    if host and host[0] == '[' and host[-1] == ']':
        host = host[1:-1]
    return (host, port)

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
    items = []
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            items.append((k, v))
    else:
        items = list(items)
        
    tmp = []
    for k, v in items:
        if encode_keys: 
            k = encode(k, charset)
        
        if not isinstance(v, (tuple, list)):
            v = [v]
            
        for v1 in v:
            if v1 is None:
                v1 = ''
            elif callable(v1):
                v1 = encode(v1(), charset)
            else:
                v1 = encode(v1, charset)
            tmp.append('%s=%s' % (urllib.quote(k), urllib.quote_plus(v1)))
    return '&'.join(tmp)
                
def encode(v, charset="utf8"):
    if isinstance(v, unicode):
        v = v.encode(charset)
    else:
        v = str(v)
    return v
    

def make_uri(base, *args, **kwargs):
    """Assemble a uri based on a base, any number of path segments, 
    and query string parameters.

    """

    # get encoding parameters
    charset = kwargs.pop("charset", "utf-8")
    safe = kwargs.pop("safe", "/:")
    encode_keys = kwargs.pop("encode_keys", True)
    
    base_trailing_slash = False
    if base and base.endswith("/"):
        base_trailing_slash = True
        base = base[:-1]
    retval = [base]
    
    # build the path
    _path = []
    trailing_slash = False       
    for s in args:
        if s is not None and isinstance(s, basestring):
            if len(s) > 1 and s.endswith('/'):
                trailing_slash = True
            else:
                trailing_slash = False
            _path.append(url_quote(s.strip('/'), charset, safe))
                   
    path_str =""
    if _path:
        path_str = "/".join([''] + _path)
        if trailing_slash:
            path_str = path_str + "/" 
    elif base_trailing_slash:
        path_str = path_str + "/" 
        
    if path_str:
        retval.append(path_str)

    params_str = url_encode(kwargs, charset, encode_keys)
    if params_str:
        retval.extend(['?', params_str])

    return ''.join(retval)


def replace_header(name, value, headers):
    idx = -1
    for i, (k, v) in enumerate(headers):
        if k.upper() == name.upper():
            idx = i
            break
    if idx >= 0:
        headers[i] = (name.title(), value)
    else:
        headers.append((name.title(), value))
    return headers

def replace_headers(new_headers, headers):
    hdrs = {}
    for (k, v) in new_headers:
        hdrs[k.upper()] = v

    found = []
    for i, (k, v) in enumerate(headers):
        ku = k.upper()
        if ku in hdrs:
            headers[i] = (k.title(), hdrs[ku])
            found.append(ku)
        if len(found) == len(new_headers):
            return

    for k, v in new_headers.items():
        if k not in found:
            headers.append((k.title(), v))
    return headers
