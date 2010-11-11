# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import re
import urlparse
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

from urlparse import urlunparse
    
from restkit.util import replace_header
from restkit.util.oauth2 import Consumer, Request, SignatureMethod_HMAC_SHA1,\
Token

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
    
    def __init__(self, path, consumer, token=None, method=None):
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
  
    def on_path(self, req):
        path = req.uri.path or "/"
        return (self.match.match(path) is not None)
        
    def on_request(self, req, tries):
        if tries < 2:
            return

        if not self.on_path(req):
            return

        headers = dict(req.headers)
        params = {}
        form = False
        if req.body and req.body is not None:
            ctype = headers.get('Content-Type')
            if ctype is not None and \
                    ctype.startswith('application/x-www-form-urlencoded'):
                # we are in a form try to get oauth params from here
                form = True
                params = dict(parse_qsl(req.body))
            
        # update params from quey parameters    
        params.update(parse_qsl(req.uri.query))
      
        raw_url = urlunparse((req.uri.scheme, req.uri.netloc,
                req.uri.path, '', '', ''))
        
        oauth_req = Request.from_consumer_and_token(self.consumer, 
                        token=self.token, http_method=req.method, 
                        http_url=raw_url, parameters=params)
                    
        oauth_req.sign_request(self.method, self.consumer, self.token)
        
        if form:
            req.body = oauth_req.to_postdata()
            req.headers = replace_header('Content-Length', len(req.body),
                    req.headers)
        elif req.method in ('GET', 'HEAD'):
            req.url = req.final_url = oauth_req.to_url()
            req.uri = urlparse.urlparse(req.url)
        else:
            oauth_headers = oauth_req.to_header()
            for k, v in list(oauth_headers.items()):
                if not isinstance(v, basestring):
                    v = str(v)
                req.headers.append((k.title(), v))
