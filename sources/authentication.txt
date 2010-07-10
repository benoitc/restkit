Authentication
==============

Restkit support for now `basic authentication`_  and `OAuth`_. But any
other authentication schema can easily be added using http filters.

Basic authentication
--------------------

Basic authentication is managed by the object :api:`restkit.filters.BasicAuth`. It's handled automatically in :api:`restkit.request` function and in :api:`restkit.resource.Resource` object if `basic_auth_url` property is True.

To use `basic authentication` in a `Resource object` you can do::

  from restkit import Resource, BasicAuth
 
  auth = BasicAuth("username", "password")
  r = Resource("http://friendpaste.com", filters=[auth])
 
Or simply use an authentication url::

  r = Resource("http://username:password@friendpaste.com")
  
OAuth
-----

Restkit OAuth is based on `simplegeo python-oauth2 module <http://github.com/simplegeo/python-oauth2>`_ So you don't need other installation to use OAuth (you can also simply use :api:`restkit.oauth2` module in your applications).
  
The OAuth filter :api:`restkit.oauth2.filter.OAuthFilter` allow you to associate a consumer per resource (path). Initalize Oauth filter with::
      
          path, consumer, token, signaturemethod)
          
`token` and `method signature` are optionnals. Consumer should be an instance of :api:`restkit.oauth2.Consumer`, token an  instance of :api:`restkit.oauth2.Token`  signature method an instance of :api:`oauth2.SignatureMethod`  (:api:`restkit.oauth2.Token` is only needed for three-legged requests.

The filter is appleid if the path match. It allows you to maintain different authorization per path. A wildcard at the indicate to the filter to match all path behind.

Example the rule `/some/resource/*` will match `/some/resource/other` and `/some/resource/other2`, while the rule `/some/resource` will only match the path `/some/resource`.

Simple client example:
~~~~~~~~~~~~~~~~~~~~~~

::

  from restkit import OAuthFilter, request
  import restkit.oauth2 as oauth

  # Create your consumer with the proper key/secret.
  consumer = oauth.Consumer(key="your-twitter-consumer-key", 
    secret="your-twitter-consumer-secret")

  # Request token URL for Twitter.
  request_token_url = "http://twitter.com/oauth/request_token"

  # Create our filter.
  auth = oauth.OAuthFilter('*', consumer)

  # The request.
  resp = request(request_token_url, filters=[auth])
  print resp.body_string()
  

If you want to add OAuth  to your `TwitterSearch` resource::

  # Create your consumer with the proper key/secret.
  consumer = oauth.Consumer(key="your-twitter-consumer-key", 
    secret="your-twitter-consumer-secret")
    
  # Create our filter.
  client = oauth.OAuthfilter('*', consumer)
    
  s = TwitterSearch(filters=[client])
  
Twitter Three-legged OAuth Example:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Below is an example from `python-oauth2 <http://github.com/simplegeo/python-oauth2>`_ of how one would go through a three-legged OAuth flow to gain access to protected resources on Twitter. This is a simple CLI script, but can be easily translated to a web application::

  import urlparse

  from restkit import request
  from restkit.filters import OAuthFilter
  import restkit.util.oauth2 as oauth

  consumer_key = 'my_key_from_twitter'
  consumer_secret = 'my_secret_from_twitter'

  request_token_url = 'http://twitter.com/oauth/request_token'
  access_token_url = 'http://twitter.com/oauth/access_token'
  authorize_url = 'http://twitter.com/oauth/authorize'

  consumer = oauth.Consumer(consumer_key, consumer_secret)

  auth = OAuthFilter('*', consumer)

  # Step 1: Get a request token. This is a temporary token that is used for 
  # having the user authorize an access token and to sign the request to obtain 
  # said access token.



  resp = request(request_token_url, filters=[auth])
  if resp.status_int != 200:
      raise Exception("Invalid response %s." % resp.status_code)

  request_token = dict(urlparse.parse_qsl(resp.body_string()))

  print "Request Token:"
  print "    - oauth_token        = %s" % request_token['oauth_token']
  print "    - oauth_token_secret = %s" % request_token['oauth_token_secret']
  print 

  # Step 2: Redirect to the provider. Since this is a CLI script we do not 
  # redirect. In a web application you would redirect the user to the URL
  # below.

  print "Go to the following link in your browser:"
  print "%s?oauth_token=%s" % (authorize_url, request_token['oauth_token'])
  print 

  # After the user has granted access to you, the consumer, the provider will
  # redirect you to whatever URL you have told them to redirect to. You can 
  # usually define this in the oauth_callback argument as well.
  accepted = 'n'
  while accepted.lower() == 'n':
      accepted = raw_input('Have you authorized me? (y/n) ')
  oauth_verifier = raw_input('What is the PIN? ')

  # Step 3: Once the consumer has redirected the user back to the oauth_callback
  # URL you can request the access token the user has approved. You use the 
  # request token to sign this request. After this is done you throw away the
  # request token and use the access token returned. You should store this 
  # access token somewhere safe, like a database, for future use.
  token = oauth.Token(request_token['oauth_token'],
      request_token['oauth_token_secret'])
  token.set_verifier(oauth_verifier)

  auth = OAuthFilter("*", consumer, token)

  resp = request(access_token_url, "POST", filters=[auth])
  access_token = dict(urlparse.parse_qsl(resp.body_string()))

  print "Access Token:"
  print "    - oauth_token        = %s" % access_token['oauth_token']
  print "    - oauth_token_secret = %s" % access_token['oauth_token_secret']
  print
  print "You may now access protected resources using the access tokens above." 
  print



.. _basic authentication: http://www.ietf.org/rfc/rfc2617.txt
.. _OAuth: http://oauth.net/