About
-----

Restkit is an HTTP resource kit for `Python <http://python.org>`_. It allows you to easily access to HTTP resource and build objects around it. It's the base of `couchdbkit <http://www.couchdbkit.org>`_ a Python `CouchDB <http://couchdb.org>`_ framework.


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
+++++++++++++++++++++++++++++++++++++++++++++++++++++

Usage example, get friendpaste page::

  from restkit import request
  resp = request('http://friendpaste.com')
  print resp.body
  print resp.status_int_
    
    
Create a simple Twitter Search resource
+++++++++++++++++++++++++++++++++++++++

Building a resource object is easy using `restkit.Resource` class. We use `simplejson <http://code.google.com/p/simplejson/>`_ to handle deserialisation
of data.

Here is the snippet::

  from restkit import Resource

  try:
      import simplejson as json
  except ImportError:
      import json # py2.6 only
    
  class TwitterSearch(Resource):
    
      def __init__(self,  pool_instance=None):
          search_url = "http://search.twitter.com"
          super(TwitterSearch, self).__init__(search_url, follow_redirect=True, 
                                          max_follow_redirect=10,
                                          pool_instance=pool_instance)

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

    
    


