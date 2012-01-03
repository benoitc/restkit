About
-----

Restkit is an HTTP resource kit for `Python <http://python.org>`_. It allows you to easily access to HTTP resource and build objects around it. It's the base of `couchdbkit <http://www.couchdbkit.org>`_ a Python `CouchDB <http://couchdb.org>`_ framework. 

Restkit is a full HTTP client using pure socket calls and its own HTTP parser. It's not based on httplib or urllib2. 

Installation
------------

Restkit requires Python 2.x superior to 2.5 and http-parser 0.5.3 or
sup.

To install restkit using pip you must make sure you have a
recent version of distribute installed::

    $ curl -O http://python-distribute.org/distribute_setup.py
    $ sudo python distribute_setup.py
    $ easy_install pip

To install or upgrade to the latest released version of restkit::

    $ pip install http-parser
    $ pip install restkit


Note: if you get an error on MacOSX try to install with the following
arguments::

    $ env ARCHFLAGS="-arch i386 -arch x86_64" pip install http-parser
  
Usage
=====

Perform HTTP call support  with `restkit.request`.
++++++++++++++++++++++++++++++++++++++++++++++++++

Usage example, get friendpaste page::

  from restkit import request
  resp = request('http://friendpaste.com')
  print resp.body_string()
  print resp.status_int
    
    
Create a simple Twitter Search resource
+++++++++++++++++++++++++++++++++++++++

Building a resource object is easy using `restkit.Resource` class. 
We use `simplejson <http://code.google.com/p/simplejson/>`_ to 
handle deserialisation of data.

Here is the snippet::

  from restkit import Resource

  try:
      import simplejson as json
  except ImportError:
      import json # py2.6 only
    
  class TwitterSearch(Resource):
    
      def __init__(self,  pool_instance=None, **kwargs):
          search_url = "http://search.twitter.com"
          super(TwitterSearch, self).__init__(search_url, follow_redirect=True, 
                                          max_follow_redirect=10,
                                          pool_instance=pool_instance,
                                          **kwargs)

      def search(self, query):
          return self.get('search.json', q=query)
        
      def request(self, *args, **kwargs):
          resp = super(TwitterSearch, self).request(*args, **kwargs)
          return json.loads(resp.body_string())
        
  if __name__ == "__main__":
      s = TwitterSearch()
      print s.search("gunicorn")

Reuses connections
------------------

Reusing connections is good. Restkit can maintain for you the http connections and
reuse them if the server allows it. To do that you can pass to any object a pool 
instance inheriting `reskit.pool.PoolInterface`. By default a threadsafe pool is
used in any application:

::

  from restkit import Resource, Manager
  
  manager = TManager(max_conn=10)
  res = Resource('http://friendpaste.com', manager=manager)


or if you use `Gevent <http://gevent.org>`_:

::

  from gevent import monkey; monkey.patch_all()

  from restkit import request
  from restkit.globals import set_manager
  from restkit.manager.mgevent import GeventManager

  set_manager(GeventManager(timeout=300))

  r = request('http://friendpaste.com')


Authentication
==============

Restkit support for now `basic authentication`_  and `OAuth`_. But any
other authentication schema can easily be added using http filters.

Basic authentication
++++++++++++++++++++


To use `basic authentication` in a `Resource object` you can do::

  from restkit import Resource, BasicAuth
 
  auth = BasicAuth("username", "password")
  r = Resource("http://friendpaste.com", filters=[auth])
 
Or simply use an authentication url::

  r = Resource("http://username:password@friendpaste.com")
  
.. _basic authentification: http://www.ietf.org/rfc/rfc2617.txt
.. _OAuth: http://oauth.net/

OAuth
+++++

Restkit OAuth is based on `simplegeo python-oauth2 module <http://github.com/simplegeo/python-oauth2>`_ So you don't need other installation to use OAuth (you can also simply use `restkit.oauth2` module in your applications).
  
The OAuth filter `restkit.oauth2.filter.OAuthFilter` allow you to associate a consumer per resource (path). Initalize Oauth filter with::
      
          path, consumer, token, signaturemethod
          
`token` and `method signature` are optionnals. Consumer should be an instance of `restkit.oauth2.Consumer`, token an  instance of `restkit.oauth2.Token`  signature method an instance of `oauth2.SignatureMethod`  (`restkit.oauth2.Token` is only needed for three-legged requests.

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

