wsgi_proxy
----------

Restkit version 1.2 introduced a WSGI proxy extension written by `gawel <http://www.gawel.org/>`_ .This extension proxy WSGI requests to a remote server.

Here is a quick example. You can read full post `here <http://www.gawel.org/weblog/en/2010/03/using_restkit_proxy_in_your_wsgi_app>`_ .

We will do here a simple proxy for `CouchDB <http://couchdb.apache.org>`_. We use `webob <http://pythonpaste.org/webob/>`_ and `gunicorn <http://gunicorn.org>`_ to launch it::

  import urlparse

  from webob import Request
  from restkit.pool import ConnectionPool
  from restkit.ext.wsgi_proxy import HostProxy

  pool = ConnectionPool(max_connections=10)
  proxy = HostProxy("http://127.0.0.1:5984", pool=pool)


  def application(environ, start_response):
      req = Request(environ)
      if 'RAW_URI' in req.environ: 
          # gunicorn so we can use real path non encoded
          u = urlparse.urlparse(req.environ['RAW_URI'])
          req.environ['PATH_INFO'] = u.path

      # do smth like adding oauth headers ..
      resp = req.get_response(proxy)

      # rewrite response
      # do auth ...
      return resp(environ, start_response)
    
    
And then launch your application::

  gunicorn -w 12 couchdbproxy:application


And access to your couchdb at `http://127.0.0.1:8000` .