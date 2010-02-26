About
-----

Restkit is an HTTP resource kit for `Python <http://python.org>`_. It allows you to easily access to HTTP resource and build objects around it. It's the base of `couchdbkit <http://www.couchdbkit.org>`_ a Python `CouchDB <http://couchdb.org>`_ framework. 

Restkit is a full HTTP client using pure socket calls and its own HTTP parser. It's not based on httplib or urllib2. 

Installation
------------

Restkit requires Python 2.x superior to 2.5.

Install from sources::

  $ python setup.py install

Or from Pypi::

  $ easy_install -U restkit
  
Usage
=====

Perform HTTP call support  with `restkit.request`.
++++++++++++++++++++++++++++++++++++++++++++++++++

Usage example, get friendpaste page::

  from restkit import request
  resp = request('http://friendpaste.com')
  print resp.body
  print resp.status_int_
    
    
Create a simple Twitter Search resource
+++++++++++++++++++++++++++++++++++++++

Building a resource object is easy using `restkit.Resource` class. We use `simplejson <http://code.google.com/p/simplejson/>`_ to handle deserialisation of data.

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
          return json.loads(resp.body)
        
  if __name__ == "__main__":
      s = TwitterSearch()
      print s.search("gunicorn")

Reuses connections
------------------

Reusing connections is good. Restkit can maintain for you the http connections and reuse them if the server allows it. To do that you can pass to any object a pool instance inheriting reskit.pool.PoolInterface. You can use our threadsafe pool in any application::


  from restkit import Resource, ConnectionPool
  
  pool = ConnectionPool(max_connections=5)
  res = Resource('http://friendpaste.com', pool_instance=pool)
  
or if you use Eventlet::

  import eventlet
  eventlet.monkey_patch(all=False, socket=True, select=True)
  
  from restkit import Resource
  from restkit.ext.eventlet_pool import EventletPool
  
  pool = EventletPool(max_connections=5, timeout=300)
  res = Resource('http://friendpaste.com', pool_instance=pool)


Using `eventlet <http://eventlet.net>`_ pool is definitely better since it allows you to define a timeout for connections. When timeout is reached and the connection is still in the pool, it will be closed.

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

Restkit OAuth is based on `simplegeo python-oauth2 module <http://github.com/simplegeo/python-oauth2>`_ So you don't need other installation to use OAuth (you can also simply use restkit.oauth2 module in your applications).
  
The OAuth filter allow you to associate a consumer per resource (path). Initalize Oauth filter with a tuple or list of tuples::
      
          (path, consumer, token, signaturemethod) 
          
`token` and `method signature` are optionnals. Consumer should be an instance of `restkit.oauth2.Consumer`, token an  instance of `restkit.oauth2.Token`  signature method an instance of `oauth2.SignatureMethod`  (`restkit.oauth2.Token` is only needed for three-legged requests.

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

