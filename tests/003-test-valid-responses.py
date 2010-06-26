# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

import t
import treq

import glob
import os
dirname = os.path.dirname(__file__)
repdir = os.path.join(dirname, "responses")

def a_case(fname):
    expect = treq.load_response_py(os.path.splitext(fname)[0] + ".py")
    resp = treq.response(fname, expect)
    for case in resp.gen_cases():
        case[0](*case[1:])

def test_http_parser():
    for fname in glob.glob(os.path.join(repdir, "*.http")):
        if os.getenv("GUNS_BLAZING"):
            expect = treq.load_response_py(os.path.splitext(fname)[0] + ".py")
            resp = treq.response(fname, expect)
            for case in resp.gen_cases():
                yield case
        else:
            yield (a_case, fname)
