# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import base64


class BasicAuth(object):
    """ Simple filter to manage basic authentification"""
    
    def __init__(self, username, password):
        self.credentials = (username, password)
    
    def on_request(self, req, tries):
        encode = base64.b64encode("%s:%s" % self.credentials)
        req.headers.append(('Authorization', 'Basic %s' %  encode))
