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
  
The OAuth filter :api:`restkit.oauth2.filter.OAuthFilter` allow you to associate a consumer per resource (path). Initalize Oauth filter with a tuple or list of tuples::
      
          (path, consumer, token, signaturemethod) 
          
`token` and `method signature` are optionnals. Consumer should be an instance of :api:`restkit.oauth2.Consumer`, token an  instance of :api:`restkit.oauth2.Token`  signature method an instance of :api:`oauth2.SignatureMethod`  (:api:`restkit.oauth2.Token` is only needed for three-legged requests.

With a list of tupple, the filter will try to match the path with the rule. It allows you to maintain different authorization per path. A wildcard at the indicate to the filter to match all path behind.

Example the rule `/some/resource/*` will match `/some/resource/other` and `/some/resource/other2`, while the rule `/some/resource` will only match the path `/some/resource`.

Simple client example:
~~~~~~~~~~~~~~~~~~~~~~

::

  from restkit import OAuthfilter, request
  import restkit.oauth2 as oauth

  # Create your consumer with the proper key/secret.
  consumer = oauth.Consumer(key="your-twitter-consumer-key", 
    secret="your-twitter-consumer-secret")

  # Request token URL for Twitter.
  request_token_url = "http://twitter.com/oauth/request_token"

  # Create our filter.
  auth = OAuthfilter(('*', consumer))

  # The request.
  resp = request(request_token_url, filters=[auth])
  print resp.body
  

If you want to add OAuth  to your `TwitterSearch` resource::

  # Create your consumer with the proper key/secret.
  consumer = oauth.Consumer(key="your-twitter-consumer-key", 
    secret="your-twitter-consumer-secret")
    
  # Create our filter.
  client = OAuthfilter(('*', consumer))
    
  s = TwitterSearch(filters=[client])


.. _basic authentication: http://www.ietf.org/rfc/rfc2617.txt
.. _OAuth: http://oauth.net/