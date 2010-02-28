.. RESTKit documentation master file, created by
   sphinx-quickstart on Fri Feb 26 23:09:27 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to RESTKit's documentation!
===================================

Restkit is an HTTP resource kit for `Python <http://python.org>`_. It allows you to easily access to HTTP resource and build objects around it. It's the base of `couchdbkit <http://www.couchdbkit.org>`_ a Python `CouchDB <http://couchdb.org>`_ framework. 

Restkit is a full HTTP client using pure socket calls and its own HTTP parser. It's not based on httplib or urllib2.

Features
--------

- Full compatible HTTP client for HTTP/1.0 HTTP/1.1
- Map HTTP resources to Python objects
- **Read** and **Send** on the fly
- Support `Chunked transfer encoding`_ in both ways.
- Support `Basic Authentification`_ and `OAuth`_.
- Multipart forms and url-encoded forms
- Proxy handling
- HTTP Filters, you can hook requests in responses with your own callback
- Compatible with Python 2.x (>= 2.5)

.. _Chunked transfer encoding: http://en.wikipedia.org/wiki/Chunked_transfer_encoding
.. _Basic Authentification: http://www.ietf.org/rfc/rfc2617.txt
.. _OAuth: http://oauth.net/