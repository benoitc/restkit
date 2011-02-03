Usage with Eventlet and Gevent
==============================

Restkit can be used with `eventlet`_ or `gevent`_ and provide specific
connection manager to manage iddle connections for them.

Use it with gevent:
-------------------

Here is a quick crawler example using Gevent::

    import timeit

    # patch python to use replace replace functions and classes with
    # cooperative ones
    from gevent import monkey; monkey.patch_all()

    import gevent

    from restkit import *
    from restkit.globals import set_manager, get_manager
    from restkit.manager.mgevent import GeventManager

    # set the gevent connection manager
    set_manager(GeventManager())

    urls = [
            "http://yahoo.fr",
            "http://google.com", 
            "http://friendpaste.com", 
            "http://benoitc.io", 
            "http://couchdb.apache.org"]

    allurls = []
    for i in range(10):
        allurls.extend(urls)

    def fetch(u):
        r = request(u, follow_redirect=True)
        print "RESULT: %s: %s (%s)" % (u, r.status, len(r.body_string()))

    def extract():
        
        jobs = [gevent.spawn(fetch, url) for url in allurls]
        gevent.joinall(jobs)

    t = timeit.Timer(stmt=extract)
    print "%.2f s" % t.timeit(number=1)

.. NOTE:
    
    You have to set the manager in the main thread so it can be used
    everywhere in your application.

Use it with eventlet:
---------------------

Same exemple as above but using eventlet::

    import timeit

    # patch python
    import eventlet 
    eventlet.monkey_patch()

    from restkit import *
    from restkit.globals import set_manager, get_manager
    from restkit.manager.meventlet import EventletManager

    # set the connection manager
    set_manager(EventletManager())

    pool = eventlet.GreenPool()

    urls = [
            "http://yahoo.fr",
            "http://google.com", 
            "http://friendpaste.com", 
            "http://benoitc.io", 
            "http://couchdb.apache.org"]

    allurls = []
    for i in range(10):
        allurls.extend(urls)

    def fetch(u):
        r = request(u, follow_redirect=True)
        print "RESULT: %s: %s (%s)" % (u, r.status, len(r.body_string()))

    def extract():
        for url in allurls:
            pool.spawn_n(fetch, url)
        pool.waitall()

    t = timeit.Timer(stmt=extract)
    print "%.2f s" % t.timeit(number=1)


.. _eventlet: http://eventlet.net
.. _gevent: http://gevent.org
