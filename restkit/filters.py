# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import base64
import re
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl
from urlparse import urlunparse

from restkit.oauth2 import Request, SignatureMethod_HMAC_SHA1

class BasicAuth(object):
    """ Simple filter to manage basic authentification"""
    
    def __init__(self, username, password):
        self.credentials = (username, password)
    
    def on_request(self, request):
        encode = base64.b64encode("%s:%s" % self.credentials)
        request.headers['Authorization'] = 'Basic %s' %  encode

def validate_consumer(consumer):
    """ validate a consumer agains oauth2.Consumer object """
    if not hasattr(consumer, "key"):
        raise ValueError("Invalid consumer.")
    return consumer
    
def validate_token(token):
    """ validate a token agains oauth2.Token object """
    if token is not None and not hasattr(token, "key"):
        raise ValueError("Invalid token.")
    return token


class OAuthFilter(object):
    """ oauth filter """

    def __init__(self, path, consumer, token=None, method=None, 
            realm=""):
        """ Init OAuthFilter
        
        :param path: path or regexp. * mean all path on wicth oauth can be
        applied.
        :param consumer: oauth consumer, instance of oauth2.Consumer
        :param token: oauth token, instance of oauth2.Token
        :param method: oauth signature method
        
        token and method signature are optionnals. Consumer should be an 
        instance of `oauth2.Consumer`, token an  instance of `oauth2.Toke` 
        signature method an instance of `oauth2.SignatureMethod`.

        """
        
        if path.endswith('*'):
            self.match = re.compile("%s.*" % path.rsplit('*', 1)[0])
        else:
            self.match = re.compile("%s$" % path)
        self.consumer = validate_consumer(consumer)
        self.token = validate_token(token)
        self.method = method or SignatureMethod_HMAC_SHA1()
        self.realm = realm
  
    def on_path(self, request):
        path = request.parsed_url.path or "/"
        return (self.match.match(path) is not None)
        
    def on_request(self, request):
        if not self.on_path(request):
            return

        params = {}
        form = False
        parsed_url = request.parsed_url

        if request.body and request.body is not None:
            ctype = request.headers.iget('content-type')
            if ctype is not None and \
                    ctype.startswith('application/x-www-form-urlencoded'):
                # we are in a form try to get oauth params from here
                form = True
                params = dict(parse_qsl(request.body))
            
        # update params from quey parameters    
        params.update(parse_qsl(parsed_url.query))
      
        raw_url = urlunparse((parsed_url.scheme, parsed_url.netloc,
                parsed_url.path, '', '', ''))
        
        oauth_req = Request.from_consumer_and_token(self.consumer, 
                        token=self.token, http_method=request.method, 
                        http_url=raw_url, parameters=params)
                    
        oauth_req.sign_request(self.method, self.consumer, self.token)
        
        if form:
            request.body = oauth_req.to_postdata()
            
            request.headers['Content-Length'] = len(request.body)
        elif request.method in ('GET', 'HEAD'):
            request.original_url = request.url
            request.url = oauth_req.to_url()
        else:
            oauth_headers = oauth_req.to_header(realm=self.realm)
            request.headers.update(oauth_headers)
