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
    
from restkit.oauth2 import Consumer, Request, SignatureMethod_HMAC_SHA1,\
Token

def validate_consumer(consumer):
    """ validate a consumer agains oauth2.Consumer object """
    if not isinstance(consumer, Consumer):
        raise ValueError("Invalid consumer.")
    return consumer
    
def validate_token(token):
    """ validate a token agains oauth2.Token object """
    if token is not None and not isinstance(token, Token):
        raise ValueError("Invalid token.")
    return token


class OAuthFilter(object):
    
    def __init__(self, rules):
        """ 
        Initalize Oauth filter wiht a tupple or list of tupples::
        
            (path, consumer, token, signaturemethod) 
        
        token and method signature are optionnals. Consumer should be an 
        instance of `oauth2.Consumer`, token an  instance of `oauth2.Toke` 
        signature method an instance of `oauth2.SignatureMethod`.
        
        With a list of tupple, the filter will try to match the path with 
        the rule. It allows you to maintain different authorization per
        path. A wildcard at the indicate to the filter to match all path
        behind.
        
        Example the rule::
        
            /some/resource/*
            
        will match :
        
            /some/resource/other
            /some/resource/other2
            
        while the rule `/some/resource` will only match the path 
        `/some/resource`.
            
            
        """
        
        if not isinstance(rules, list):
            self.rules = [rules]
        else:
            self.rules = rules
        self.resources = {}
        self.matches = []
        self.parse_rules()
        
    def parse_rules(self):
        for rule in self.rules:
            self.add_rule(rule)
            
    def add_rule(self, rule):
        default_method = SignatureMethod_HMAC_SHA1()
        if len(rule) == 2:
            # path, consumer
            r = (validate_consumer(rule[1]), None, default_method)
        elif len(rule) == 3:
            r = (validate_consumer(rule[1]), validate_token(rule[2]), 
                default_method)
        elif len(rule) == 4:
            r = (validate_consumer(rule[1]), validate_token(rule[2]), 
                rule[3] or default_method)
        else:
            raise ValueError("Invalid OAUTH resource.")
            
        path = rule[0]
        if path.endswith('*'):
            re_path = re.compile("%s.*" % path.rsplit('*', 1)[0])
        else:
            re_path = re.compile("%s$" % path)
        self.matches.append(re_path)
        self.resources[re_path] = r
     
    def on_path(self, req):
        path = req.uri.path or "/"
        for m in self.matches:
            if m.match(path) is not None:
                return self.resources[m]
        return False
        
    def on_request(self, req):
        resource = self.on_path(req)
        if not resource:
            return
        consumer, token, method = resource
        
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
        
        oauth_req = Request.from_consumer_and_token(consumer, token=token, 
                        http_method=req.method, http_url=req.url, 
                        parameters=params)
                    
        oauth_req.sign_request(method, consumer, token)
        
        if form:
            req.body = oauth_req.to_postdata()
        elif req.method in ('GET', 'HEAD'):
            req.url = req.final_url = oauth_req.to_url()
            req.uri = urlparse.urlparse(req.url)
        else:
            oauth_headers = oauth_req.to_header()
            for k, v in list(oauth_headers.items()):
                if not isinstance(v, basestring):
                    v = str(v)
                req.headers.append((k.title(), v))