# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import sys
from restkit.encoding import DEFAULT_ENCODING

orig_open = open
PY3 = sys.version_info[0] == 3
def no_code(x, encoding=None):
    return x

def decode(s, encoding=None):
    encoding = encoding or DEFAULT_ENCODING
    return s.decode(encoding, "replace")

def encode(u, encoding=None):
    encoding = encoding or DEFAULT_ENCODING
    return u.encode(encoding, "replace")


def cast_unicode(s, encoding=None):
    if isinstance(s, bytes):
        return decode(s, encoding)
    return s

def cast_bytes(s, encoding=None):
    if not isinstance(s, bytes):
        return encode(s, encoding)
    return s

if PY3:
    string_types = str,
    integer_types = int,
    text_type = str

    def b2s(s):
        return s.decode('latin1')

    def s2b(s):
        return s.encode('latin1')

    str_to_unicode = no_code
    unicode_to_str = no_code
    str_to_bytes = encode
    bytes_to_str = decode
    cast_bytes_py2 = no_code


    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO

    def raise_with_tb(E, V, T):
        raise E(V).with_traceback(T)

    MAXSIZE = sys.maxsize

    import urllib.parse
    urlparse = urllib.parse.urlparse
    urlunparse = urllib.parse.urlunparse
    urlsplit = urllib.parse.urlsplit
    urlunsplit = urllib.parse.urlunsplit
    parse_qsl = urllib.parse.parse_qsl
    parse_qs = urllib.parse.parse_qs
    quote = urllib.parse.quote
    quote_plus = urllib.parse.quote_plus
    unquote = urllib.parse.unquote
    urlencode = urllib.parse.urlencode
    urljoin = urllib.parse.urljoin

    import collections
    def iscallable(v):
        return isinstance(v, collections.Callable)

    open = orig_open

    def execfile(fname, glob, loc=None):
        loc = loc if (loc is not None) else glob
        with open(fname, 'rb') as f:
            exec(compile(f.read(), fname, 'exec'), glob, loc)

    import http.cookies
    Cookie = http.cookies
    import queue
    Queue = queue

    def iteritems_(d):
        return d.items()

    def itervalues_(d):
        return d.values()

else:
    string_types = basestring,
    integer_types = (int, long)
    text_type = unicode

    def b2s(s):
        return s

    def s2b(s):
        return s

    str_to_unicode = decode
    unicode_to_str = encode
    str_to_bytes = no_code
    bytes_to_str = no_code
    cast_bytes_py2 = cast_bytes

    import StringIO
    StringIO = StringIO.StringIO

    BytesIO = StringIO

    def raise_with_tb(E, V, T):
        raiseE, V, T


    # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
    class X(object):
        def __len__(self):
            return 1 << 31
    try:
        len(X())
    except OverflowError:
        # 32-bit
        MAXSIZE = int((1 << 31) - 1)
    else:
        # 64-bit
        MAXSIZE = int((1 << 63) - 1)
    del X

    import urlparse as orig_urlparse
    urlparse = orig_urlparse.urlparse
    urlunparse = orig_urlparse.urlunparse
    urlsplit = orig_urlparse.urlsplit
    urlunsplit = orig_urlparse.urlunsplit
    parse_qsl = orig_urlparse.parse_qsl
    parse_qs = orig_urlparse.parse_qs
    urljoin = orig_urlparse.urljoin

    import urllib
    quote = urllib.quote
    quote_plus = urllib.quote_plus
    unquote = urllib.unquote
    urlencode = urllib.urlencode

    iscallable = callable

    if sys.platform == 'win32':
        def execfile(fname, glob=None, loc=None):
            loc = loc if (loc is not None) else glob
            # The rstrip() is necessary b/c trailing whitespace in files will
            # cause an IndentationError in Python 2.6 (this was fixed in 2.7,
            # but we still support 2.6).  See issue 1027.
            scripttext = __builtin__.open(fname).read().rstrip() + '\n'
            # compile converts unicode filename to str assuming
            # ascii. Let's do the conversion before calling compile
            if isinstance(fname, unicode):
                filename = unicode_to_str(fname)
            else:
                filename = fname
            exec(compile(scripttext, filename, 'exec'), glob, loc)
    else:
        def execfile(fname, *where):
            if isinstance(fname, unicode):
                filename = fname.encode(sys.getfilesystemencoding())
            else:
                filename = fname
            __builtin__.execfile(filename, *where)

    import Cookie
    Cookie = Cookie

    import Queue
    Queue = Queue

    def iteritems_(d):
        return d.iteritems()

    def itervalues_(d):
        return d.itervalues()
