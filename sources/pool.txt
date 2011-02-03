Reuses connections
==================

Reusing connections is good. Restkit can maintain for you the http connections and reuse them if the server allows it. To do that you can pass to any object a connection manager instance inheriting :api:`reskit.manager.Manager`. By default the manager signaling to close iddle connections::


  from restkit import Resource, Manager
  
  manager = TManager(max_conn=10)
  res = Resource('http://friendpaste.com', manager=manager)

.. NOTE::
    
    By default, restkit keep 10 connections alive.
  
Restkit provides also Pool working with `eventlet <http://eventlet.net>`_ or `gevent <http://gevent.net>`_.

Example of usage with Gevent::

  from gevent import monkey; monkey.patch_all()

  from restkit import request
  from restkit.globals import set_manager
  from restkit.manager.mgevent import GeventManager

  set_manager(GeventManager(timeout=300))

  r = request('http://friendpaste.com')

This is likely the same with Eventlet::

  import eventlet 
  eventlet.monkey_patch() #we patch eventlet

  from restkit import Resource
  from restkit.globals import set_manager
  from restkit.manager.meventlet import EventletManager
  
  set_manager(EventletManager(timeout=300))
  res = Resource('http://friendpaste.com')
  
