wsgi_proxy
----------

Restkit version 1.2 introduced a WSGI proxy extension written by `Gael
Pasgrimaud <http://www.gawel.org/>`_ .This extension proxy WSGI requests to a
remote server.

Here is a quick example. You can read full post `here
<http://www.gawel.org/weblog/en/2010/03/using_restkit_proxy_in_your_wsgi_app>`_
.

We will do here a simple proxy for `CouchDB <http://couchdb.apache.org>`_. We
use `webob <http://pythonpaste.org/webob/>`_ and `gunicorn
<http://gunicorn.org>`_ to launch it::

  import urlparse

  from webob import Request
  from restkit.conn import TConnectionManager
  from restkit.ext.wsgi_proxy import HostProxy

  mgr = TConnectionManager(nb_connections=10)
  proxy = HostProxy("http://127.0.0.1:5984", pool=mgr)


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

  gunicorn -w 12 -a "egg:gunicorn#eventlet" couchdbproxy:application


And access to your couchdb at `http://127.0.0.1:8000` .

You can also use a Paste configuration::

  [app:proxy]
  use = egg:restkit#host_proxy
  uri = http://www.example.com/example_db
  strip_script_name = false
  allowed_methods = get

Here is a more advanced example to show how to use the Proxy class to build a
distributed proxy. `/a/db` will proxify `http://a.mypool.org/db`::

  import urlparse

  from webob import Request
  from restkit.conn import TConnectionManager
  from restkit.ext.wsgi_proxy import Proxy

  mgr = TConnectionManager(nb_connections=10)

  proxy = Proxy(pool=mgr, strip_script_name=True)


  def application(environ, start_response):
      req = Request(environ).copy()
      req.path_info_pop()
      req.environ['SERVER_NAME'] = '%s.mypool.org:80' % req.script_name.strip('/')
      resp = req.get_response(Proxy)
      return resp(environ, start_response)

