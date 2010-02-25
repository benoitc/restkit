About
-----

Restkit is an HTTP resource kit for `Python <http://python.org>`_. It allows you to easily access to HTTP resource and build objects around it. It's the base of `couchdbkit <http://www.couchdbkit.org>`_ a Python `CouchDB <http://couchdb.org>`_ framework.


Installation
------------

Restkit requires Python 2.x superior to 2.5.

Install from sources::

    $ python setup.py install

Or from Pypi::

  $ easy_install -U restkit
  
Usage
=====

Perform HTTP call support  with `restkit.request`.
+++++++++++++++++++++++++++++++++++++++++++++++++++++

Usage example, get friendpaste page::

    from restkit import request
    resp = request('http://friendpaste.com')
    print resp.body
    print resp.status_int_
    




    
    


