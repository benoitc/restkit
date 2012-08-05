# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import sys
from restkit.encoding import DEFAULT_ENCODING


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

    import urlparse
    urlparse = urlparse.urlparse
    urlunparse = urlparse.urlunparse
    urlsplit = urlparse.urlsplit
    urlunsplit = urlparse.urlunsplit
    parse_qsl = urlparse.parse_qsl
    parse_qs = urlparse.parse_qs
    urljoin = urlparse.urljoin

    import urllib
    quote = urllib.quote
    quote_plus = urllib.quote_plus
    unquote = urllib.unquote
    urlencode = urllib.encode

    iscallable = callable
