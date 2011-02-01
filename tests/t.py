# -*- coding: utf-8 -
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import os
from StringIO import StringIO
import tempfile

dirname = os.path.dirname(__file__)

from restkit.client import Client
from restkit.resource import Resource

from _server_test import HOST, PORT, run_server_test
run_server_test()

def data_source(fname):
    buf = StringIO()
    with open(fname) as handle:
        for line in handle:
            line = line.rstrip("\n").replace("\\r\\n", "\r\n")
            buf.write(line)
        return buf
        
        
class FakeSocket(object):
    
    def __init__(self, data):
        self.tmp = tempfile.TemporaryFile()
        if data:
            self.tmp.write(data.getvalue())
            self.tmp.flush()
            self.tmp.seek(0)

    def fileno(self):
        return self.tmp.fileno()
        
    def len(self):
        return self.tmp.len
        
    def recv(self, length=None):
        return self.tmp.read()
        
    def recv_into(self, buf, length):
        tmp_buffer = self.tmp.read(length)
        v = len(tmp_buffer)
        for i, c in enumerate(tmp_buffer):
            buf[i] = c
        return v
        
    def send(self, data):
        self.tmp.write(data)
        self.tmp.flush()
        
    def seek(self, offset, whence=0):
        self.tmp.seek(offset, whence)
                
class client_request(object):
    
    def __init__(self, path):
        if path.startswith("http://") or path.startswith("https://"):
            self.url = path
        else:
            self.url = 'http://%s:%s%s' % (HOST, PORT, path)
        
    def __call__(self, func):
        def run():
            cli = Client(timeout=300)
            func(self.url, cli)
        run.func_name = func.func_name
        return run
        
class resource_request(object):
    
    def __init__(self, url=None):
        if url is not None:
            self.url = url
        else:
            self.url = 'http://%s:%s' % (HOST, PORT)
        
    def __call__(self, func):
        def run():
            res = Resource(self.url)
            func(res)
        run.func_name = func.func_name
        return run
        
        
def eq(a, b):
    assert a == b, "%r != %r" % (a, b)

def ne(a, b):
    assert a != b, "%r == %r" % (a, b)

def lt(a, b):
    assert a < b, "%r >= %r" % (a, b)

def gt(a, b):
    assert a > b, "%r <= %r" % (a, b)

def isin(a, b):
    assert a in b, "%r is not in %r" % (a, b)

def isnotin(a, b):
    assert a not in b, "%r is in %r" % (a, b)

def has(a, b):
    assert hasattr(a, b), "%r has no attribute %r" % (a, b)

def hasnot(a, b):
    assert not hasattr(a, b), "%r has an attribute %r" % (a, b)

def raises(exctype, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exctype:
        pass
    else:
        func_name = getattr(func, "func_name", "<builtin_function>")
        raise AssertionError("Function %s did not raise %s" % (
            func_name, exctype.__name__))

