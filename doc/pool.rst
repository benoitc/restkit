Reuses connections
==================

Reusing connections is good. Restkit can maintain for you the http
connections and reuse them if the server allows it. To do that restkit
is using the `socketpool module
<https://github.com/benoitc/socketpool>`_ ::

    from restkit import *
    from socketpool import ConnectionPool

    pool = ConnectionPool(factory=Connection)

    r = request("http://someurl", pool=pool)

.. NOTE::
    
    By default, restkit use a generic session object globaly abvailable. 
    You can change its settings by using the
    **restkit.sesssion.set_session** function.
  
Restkit provides also Pool working with `eventlet <http://eventlet.net>`_ or `gevent <http://gevent.net>`_.

Example of usage with Gevent::

     from restkit import *
     from socketpool import ConnectionPool
     
     # set a pool with a gevent packend
     pool = ConnectionPool(factory=Connection, backend="gevent")

Replace **gevent** by **eventlet** for eventlet support.
