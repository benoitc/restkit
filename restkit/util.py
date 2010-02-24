# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import time
import urllib
import warnings

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None,
             'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
             
        
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
    
class deprecated_property(object):
    """
    Wraps a decorator, with a deprecation warning or error
    """
    def __init__(self, decorator, attr, message, warning=True):
        self.decorator = decorator
        self.attr = attr
        self.message = message
        self.warning = warning

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        self.warn()
        return self.decorator.__get__(obj, type)

    def __set__(self, obj, value):
        self.warn()
        self.decorator.__set__(obj, value)

    def __delete__(self, obj):
        self.warn()
        self.decorator.__delete__(obj)

    def __repr__(self):
        return '<Deprecated attribute %s: %r>' % (
            self.attr,
            self.decorator)

    def warn(self):
        if not self.warning:
            raise DeprecationWarning(
                'The attribute %s is deprecated: %s' % (self.attr, self.message))
        else:
            warnings.warn(
                'The attribute %s is deprecated: %s' % (self.attr, self.message),
                DeprecationWarning,
                stacklevel=3)