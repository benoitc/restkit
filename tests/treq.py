# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of the pywebmachine package released
# under the MIT license.



from . import t

import inspect
import os
import random
from io import StringIO
import urllib.parse

from restkit.datastructures import MultiDict 
from restkit.errors import ParseException
from restkit.http import Request, Unreader

class IterUnreader(Unreader):

    def __init__(self, iterable, **kwargs):
        self.buf = StringIO()
        self.iter = iter(iterable)
        

    def _data(self):
        if not self.iter:
            return ""
        try:
            return next(self.iter)
        except StopIteration:
            self.iter = None
            return ""
     

dirname = os.path.dirname(__file__)
random.seed()

def uri(data):
    ret = {"raw": data}
    parts = urllib.parse.urlparse(data)
    ret["scheme"] = parts.scheme or None
    ret["host"] = parts.netloc.rsplit(":", 1)[0] or None
    ret["port"] = parts.port or 80
    if parts.path and parts.params:
        ret["path"] = ";".join([parts.path, parts.params])
    elif parts.path:
        ret["path"] = parts.path
    elif parts.params:
        # Don't think this can happen
        ret["path"] = ";" + parts.path
    else:
        ret["path"] = None
    ret["query"] = parts.query or None
    ret["fragment"] = parts.fragment or None
    return ret

    
def load_response_py(fname):
    config = globals().copy()
    config["uri"] = uri
    exec(compile(open(fname).read(), fname, 'exec'), config)
    return config["response"]

class response(object):
    def __init__(self, fname, expect):
        self.fname = fname
        self.name = os.path.basename(fname)

        self.expect = expect
        if not isinstance(self.expect, list):
            self.expect = [self.expect]

        with open(self.fname) as handle:
            self.data = handle.read()
        self.data = self.data.replace("\n", "").replace("\\r\\n", "\r\n")
        self.data = self.data.replace("\\0", "\000")

    # Functions for sending data to the parser.
    # These functions mock out reading from a
    # socket or other data source that might
    # be used in real life.

    def send_all(self):
        yield self.data

    def send_lines(self):
        lines = self.data
        pos = lines.find("\r\n")
        while pos > 0:
            yield lines[:pos+2]
            lines = lines[pos+2:]
            pos = lines.find("\r\n")
        if len(lines):
            yield lines

    def send_bytes(self):
        for d in self.data:
            yield d
    
    def send_random(self):
        maxs = len(self.data) / 10
        read = 0
        while read < len(self.data):
            chunk = random.randint(1, maxs)
            yield self.data[read:read+chunk]
            read += chunk                

    # These functions define the sizes that the
    # read functions will read with.

    def size_all(self):
        return -1
    
    def size_bytes(self):
        return 1
    
    def size_small_random(self):
        return random.randint(0, 4)
    
    def size_random(self):
        return random.randint(1, 4096)

    # Match a body against various ways of reading
    # a message. Pass in the request, expected body
    # and one of the size functions.

    def szread(self, func, sizes):
        sz = sizes()
        data = func(sz)
        if sz >= 0 and len(data) > sz:
            raise AssertionError("Read more than %d bytes: %s" % (sz, data))
        return data

    def match_read(self, req, body, sizes):
        data = self.szread(req.body.read, sizes)
        count = 1000
        while len(body):
            if body[:len(data)] != data:
                raise AssertionError("Invalid body data read: %r != %r" % (
                                        data, body[:len(data)]))
            body = body[len(data):]
            data = self.szread(req.body.read, sizes)
            if not data:
                count -= 1
            if count <= 0:
                raise AssertionError("Unexpected apparent EOF")

        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        elif len(data):
            raise AssertionError("Read beyond expected body: %r" % data)        
        data = req.body.read(sizes())
        if data:
            raise AssertionError("Read after body finished: %r" % data)

    def match_readline(self, req, body, sizes):
        data = self.szread(req.body.readline, sizes)
        count = 1000
        while len(body):
            if body[:len(data)] != data:
                raise AssertionError("Invalid data read: %r" % data)
            if '\n' in data[:-1]:
                raise AssertionError("Embedded new line: %r" % data)
            body = body[len(data):]
            data = self.szread(req.body.readline, sizes)
            if not data:
                count -= 1
            if count <= 0:
                raise AssertionError("Apparent unexpected EOF")
        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        elif len(data):
            raise AssertionError("Read beyond expected body: %r" % data)        
        data = req.body.readline(sizes())
        if data:
            raise AssertionError("Read data after body finished: %r" % data)

    def match_readlines(self, req, body, sizes):
        """\
        This skips the sizes checks as we don't implement it.
        """
        data = req.body.readlines()
        for line in data:
            if '\n' in line[:-1]:
                raise AssertionError("Embedded new line: %r" % line)
            if line != body[:len(line)]:
                raise AssertionError("Invalid body data read: %r != %r" % (
                                                    line, body[:len(line)]))
            body = body[len(line):]
        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        data = req.body.readlines(sizes())
        if data:
            raise AssertionError("Read data after body finished: %r" % data)
    
    def match_iter(self, req, body, sizes):
        """\
        This skips sizes because there's its not part of the iter api.
        """
        for line in req.body:
            if '\n' in line[:-1]:
                raise AssertionError("Embedded new line: %r" % line)
            if line != body[:len(line)]:
                raise AssertionError("Invalid body data read: %r != %r" % (
                                                    line, body[:len(line)]))
            body = body[len(line):]
        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        try:
            data = next(iter(req.body))
            raise AssertionError("Read data after body finished: %r" % data)
        except StopIteration:
            pass

    # Construct a series of test cases from the permutations of
    # send, size, and match functions.
    
    def gen_cases(self):
        def get_funs(p):
            return [v for k, v in inspect.getmembers(self) if k.startswith(p)]
        senders = get_funs("send_")
        sizers = get_funs("size_")
        matchers = get_funs("match_")
        cfgs = [
            (mt, sz, sn)
            for mt in matchers
            for sz in sizers
            for sn in senders
        ]

        ret = []
        for (mt, sz, sn) in cfgs:
            mtn = mt.__name__[6:]
            szn = sz.__name__[5:]
            snn = sn.__name__[5:]
            def test_req(sn, sz, mt):
                self.check(sn, sz, mt)
            desc = "%s: MT: %s SZ: %s SN: %s" % (self.name, mtn, szn, snn)
            test_req.description = desc
            ret.append((test_req, sn, sz, mt))
        return ret

    def check(self, sender, sizer, matcher):
        cases = self.expect[:]

        unreader = IterUnreader(sender())
        resp = Request(unreader)
        self.same(resp, sizer, matcher, cases.pop(0))
        t.eq(len(cases), 0)

    def same(self, resp, sizer, matcher, exp):
        t.eq(resp.status, exp["status"])
        t.eq(resp.version, exp["version"])
        t.eq(resp.headers, MultiDict(exp["headers"]))
        matcher(resp, exp["body"], sizer)
        t.eq(resp.trailers, exp.get("trailers", []))
