.. _doc:

Documentation
=============
You can do simply use  :api:`restkit.request` function to do any HTTP requests.

Usage example, get friendpaste page::

  from restkit import request
  resp = request('http://friendpaste.com')
  print resp.body


but you can do more like building object mapping HTTP resources, ....

.. toctree::
   :maxdepth: 2
   
   resource
   pool
   authentication
   client