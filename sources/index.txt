.. RESTKit documentation master file, created by
   sphinx-quickstart on Fri Feb 26 23:09:27 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to RESTKit's documentation!
===================================

Restkit is an HTTP resource kit for `Python <http://python.org>`_. It allows you to easily access to HTTP resource and build objects around it. It's the base of `couchdbkit <http://www.couchdbkit.org>`_ a Python `CouchDB <http://couchdb.org>`_ framework. 

You can simply use  :api:`restkit.request` function to do any HTTP requests.

Usage example, get a friendpaste paste::

  >>> from restkit import request
  >>> r = request('http://friendpaste.com/1ZSEoJeOarc3ULexzWOk5Y_633433316631/raw')
  >>> r.body_string()
  'welcome to friendpaste'
  >>> r.headers
  {'status': '200 OK', 'transfer-encoding': 'chunked', 'set-cookie': 
  'FRIENDPASTE_SID=b581975029d689119d3e89416e4c2f6480a65d96; expires=Sun,
  14-Mar-2010 03:29:31 GMT; Max-Age=1209600; Path=/', 'server': 'nginx/0.7.62',
  'connection': 'keep-alive', 'date': 'Sun, 28 Feb 2010 03:29:31 GMT',
  'content-type': 'text/plain'}
  
of from a resource:

  >>> from restkit import Resource
  >>> res = Resource('http://friendpaste.com')
  >>> r = res.get('/1ZSEoJeOarc3ULexzWOk5Y_633433316631/raw')
  >>> r.body_string()
  'welcome to friendpaste'
  
but you can do more like building object mapping HTTP resources, ....


.. toctree::
   :maxdepth: 2 
   
   resource
   pool
   authentication
   streaming
   green
   client
   shell
   wsgi_proxy


Features
--------

- Full compatible HTTP client for HTTP 1.0 and 1.1
- Threadsafe
- Use pure socket calls and its own HTTP parser (It's not based on httplib or urllib2)
- Map HTTP resources to Python objects
- **Read** and **Send** on the fly
- Reuses connections
- `Eventlet <http://www.eventlet.net>`_ and `Gevent <http://www.gevent.org>`_ support
- Support `Chunked transfer encoding`_ in both ways.
- Support `Basic Authentification`_ and `OAuth`_.
- Multipart forms and url-encoded forms
- Proxy handling
- HTTP Filters, you can hook requests in responses with your own callback
- Compatible with Python 2.x (>= 2.5)

.. _Chunked transfer encoding: http://en.wikipedia.org/wiki/Chunked_transfer_encoding
.. _Basic Authentification: http://www.ietf.org/rfc/rfc2617.txt
.. _OAuth: http://oauth.net/
