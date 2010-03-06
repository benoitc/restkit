Reuses connections
==================

Reusing connections is good. Restkit can maintain for you the http connections and reuse them if the server allows it. To do that you can pass to any object a pool instance inheriting :api:`reskit.pool.PoolInterface`. You can use our threadsafe pool in any application::


  from restkit import Resource, ConnectionPool
  
  pool = ConnectionPool(max_connections=5)
  res = Resource('http://friendpaste.com', pool_instance=pool)
  
Restkit provides also Pool working with `eventlet <http://eventlet.net>`_ or `gevent <http://gevent.net>`_.

Example of usage with Gevent::

  from restkit import *
  from gevent import monkey; monkey.patch_socket()
  from restkit.ext.gevent_pool import GeventPool
  pool = GeventPool(max_connections=5, timeout=300)
  r = request('http://friendpaste.com', pool_instance=pool)

This is likely the same with Eventlet::

  import eventlet
  eventlet.monkey_patch(all=False, socket=True, select=True)
  
  from restkit import Resource
  from restkit.ext.eventlet_pool import EventletPool
  
  pool = EventletPool(max_connections=5, timeout=300)
  res = Resource('http://friendpaste.com', pool_instance=pool)
  
Using `Eventlet` or `Gevent` pools is definitely better since it allows you to define a timeout for connections. When timeout is reached and the connection is still in the pool, it will be closed.