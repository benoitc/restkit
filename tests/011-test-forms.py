# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import os
import uuid
import t
from restkit import request
from restkit.forms import multipart_form_encode

from _server_test import HOST, PORT

def test_001():
    u = "http://%s:%s/multipart2" % (HOST, PORT)
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    l = int(os.fstat(f.fileno())[6])
    b = {'a':'aa','b':['bb','cc'], 'f':f}
    h = {'content-type':"multipart/form-data"}
    body, headers = multipart_form_encode(b, h, uuid.uuid4().hex)
    r = request(u, method='POST', body=body, headers=headers)
    t.eq(r.status_int, 200)
    t.eq(int(r.body_string()), l)