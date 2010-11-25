Reuses connections
==================

Reusing connections is good. Restkit can maintain for you the http connections and reuse them if the server allows it. To do that you can pass to any object a connection manager instance inheriting :api:`reskit.conn.base.ConnManager`. You can use our threadsafe pool in any application::


  from restkit import Resource, TConnectionManager
  
  manager = TConnectionManager(nb_connections=10)
  res = Resource('http://friendpaste.com', conn_manager=manager)

.. NOTE::
    
    By default, restkit is using the threadsafe connections manager 
    and keep 10 connections alive.
  
Restkit provides also Pool working with `eventlet <http://eventlet.net>`_ or `gevent <http://gevent.net>`_.

Example of usage with Gevent::

  from restkit import request 
  from restkit.conn.gevent_manager import GeventConnectionManager
  manager = GeventConnectionManager(timeout=300, nb_connections=10)
  r = request('http://friendpaste.com', conn_manager=manager)

This is likely the same with Eventlet::

  from restkit import Resource
  from restkit.conn.eventlet_manager import EventletConnectionManager
  
  manager = EventletConnectionManager(timeout=300, nb_connections=300)
  res = Resource('http://friendpaste.com', conn_manager=manager)
  
