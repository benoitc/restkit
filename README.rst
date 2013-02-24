About
-----

Restkit is an HTTP resource kit for `Python <http://python.org>`_. It allows
you to easily access to HTTP resource and build objects around it. It's the
base of `couchdbkit <http://www.couchdbkit.org>`_ a Python `CouchDB
<http://couchdb.org>`_ framework.

Restkit is a full HTTP client using pure socket calls and its own HTTP parser.
It's not based on httplib or urllib2.

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
- Streaming support
- Proxy handling
- HTTP Filters, you can hook requests in responses with your own callback
- Compatible with Python 2.x (>= 2.6)

Documentation
-------------

http://restkit.readthedocs.org


Installation
------------

restkit requires Python 2.x superior to 2.6 (Python 3 support is coming soon)

To install restkit using pip you must make sure you have a
recent version of distribute installed::

    $ curl -O http://python-distribute.org/distribute_setup.py
    $ sudo python distribute_setup.py
    $ easy_install pip


To install from source, run the following command::

    $ git clone https://github.com/benoitc/restkit.git
    $ cd restkit
    $ pip install -r requirements.txt
    $ python setup.py install

From pypi::

    $ pip install restkit

License
-------

restkit is available under the MIT license.

.. _Chunked transfer encoding: http://en.wikipedia.org/wiki/Chunked_transfer_encoding
.. _Basic Authentification: http://www.ietf.org/rfc/rfc2617.txt
.. _OAuth: http://oauth.net/
