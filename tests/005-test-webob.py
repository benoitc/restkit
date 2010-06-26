# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import unittest

import webob.exc
from restkit.contrib.webob_helper import wrap_exceptions


wrap_exceptions()

class ResourceTestCase(unittest.TestCase):
        
    def testWebobException(self):
       
        from restkit.errors import ResourceError
        self.assert_(issubclass(ResourceError, 
                webob.exc.WSGIHTTPException) == True)
        
if __name__ == '__main__':
    unittest.main()