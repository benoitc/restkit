# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

try:
    from UserDict import DictMixin
except ImportError:    
    from collections import MutableMapping as DictMixin
 
 
class MultiDict(DictMixin):

    """
        An ordered dictionary that can have multiple values for each key.
        Adds the methods getall, getone, mixed and extend and add to the normal
        dictionary interface.
    """

    def __init__(self, *args, **kw):
        if len(args) > 1:
            raise TypeError("MultiDict can only be called with one positional argument")
        if args:
            if isinstance(args[0], MultiDict):
                items = args[0]._items
            elif hasattr(args[0], 'iteritems'):
                items = list(args[0].iteritems())
            elif hasattr(args[0], 'items'):
                items = args[0].items()
            else:
                items = list(args[0])
            self._items = items
        else:
            self._items = []
        if kw:
            self._items.extend(kw.iteritems())

    @classmethod
    def from_fieldstorage(cls, fs):
        """
        Create a dict from a cgi.FieldStorage instance
        """
        obj = cls()
        # fs.list can be None when there's nothing to parse
        for field in fs.list or ():
            if field.filename:
                obj.add(field.name, field)
            else:
                obj.add(field.name, field.value)
        return obj

    def __getitem__(self, key):
        for k, v in reversed(self._items):
            if k == key:
                return v
        raise KeyError(key)

    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError:
            pass
        self._items.append((key, value))

    def add(self, key, value):
        """
        Add the key and value, not overwriting any previous value.
        """
        self._items.append((key, value))

    def getall(self, key):
        """
        Return a list of all values matching the key (may be an empty list)
        """
        return [v for k, v in self._items if k == key]

    def iget(self, key):
        """like get but case insensitive """
        lkey = key.lower()
        for k, v in self._items:
            if k.lower() == lkey:
                return v
        return None

    def getone(self, key):
        """
        Get one value matching the key, raising a KeyError if multiple
        values were found.
        """
        v = self.getall(key)
        if not v:
            raise KeyError('Key not found: %r' % key)
        if len(v) > 1:
            raise KeyError('Multiple values match %r: %r' % (key, v))
        return v[0]

    def mixed(self):
        """
        Returns a dictionary where the values are either single
        values, or a list of values when a key/value appears more than
        once in this dictionary.  This is similar to the kind of
        dictionary often used to represent the variables in a web
        request.
        """
        result = {}
        multi = {}
        for key, value in self.iteritems():
            if key in result:
                # We do this to not clobber any lists that are
                # *actual* values in this dictionary:
                if key in multi:
                    result[key].append(value)
                else:
                    result[key] = [result[key], value]
                    multi[key] = None
            else:
                result[key] = value
        return result

    def dict_of_lists(self):
        """
        Returns a dictionary where each key is associated with a list of values.
        """
        r = {}
        for key, val in self.iteritems():
            r.setdefault(key, []).append(val)
        return r

    def __delitem__(self, key):
        items = self._items
        found = False
        for i in range(len(items)-1, -1, -1):
            if items[i][0] == key:
                del items[i]
                found = True
        if not found:
            raise KeyError(key)

    def __contains__(self, key):
        for k, v in self._items:
            if k == key:
                return True
        return False

    has_key = __contains__

    def clear(self):
        self._items = []

    def copy(self):
        return self.__class__(self)

    def setdefault(self, key, default=None):
        for k, v in self._items:
            if key == k:
                return v
        self._items.append((key, default))
        return default

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError, "pop expected at most 2 arguments, got "\
                              + repr(1 + len(args))
        for i in range(len(self._items)):
            if self._items[i][0] == key:
                v = self._items[i][1]
                del self._items[i]
                return v
        if args:
            return args[0]
        else:
            raise KeyError(key)

    def ipop(self, key, *args):
        """ like pop but case insensitive """
        if len(args) > 1:
            raise TypeError, "pop expected at most 2 arguments, got "\
                              + repr(1 + len(args))

        lkey = key.lower()
        for i, item in enumerate(self._items):
            if item[0].lower() == lkey:
                v = self._items[i][1]
                del self._items[i]
                return v
        if args:
            return args[0]
        else:
            raise KeyError(key)

    def popitem(self):
        return self._items.pop()

    def extend(self, other=None, **kwargs):
        if other is None:
            pass
        elif hasattr(other, 'items'):
            self._items.extend(other.items())
        elif hasattr(other, 'keys'):
            for k in other.keys():
                self._items.append((k, other[k]))
        else:
            for k, v in other:
                self._items.append((k, v))
        if kwargs:
            self.update(kwargs)

    def __repr__(self):
        items = ', '.join(['(%r, %r)' % v for v in self.iteritems()])
        return '%s([%s])' % (self.__class__.__name__, items)

    def __len__(self):
        return len(self._items)

    ##
    ## All the iteration:
    ##

    def keys(self):
        return [k for k, v in self._items]

    def iterkeys(self):
        for k, v in self._items:
            yield k

    __iter__ = iterkeys

    def items(self):
        return self._items[:]

    def iteritems(self):
        return iter(self._items)

    def values(self):
        return [v for k, v in self._items]

    def itervalues(self):
        for k, v in self._items:
            yield v


