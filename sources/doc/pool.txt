Reuses connections
==================

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