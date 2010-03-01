.. _doc:

Documentation
=============
You can simply use  :api:`restkit.request` function to do any HTTP requests.

Usage example, get a friendpaste paste::

  >>> from restkit import request
  >>> r = request('http://friendpaste.com/1ZSEoJeOarc3ULexzWOk5Y_633433316631/raw')
  >>> r.body
  'welcome to friendpaste'
  >>> r.body_file.read()
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
  >>> r.body
  'welcome to friendpaste'
  
but you can do more like building object mapping HTTP resources, ....

.. toctree::
   :maxdepth: 2
   
   resource
   pool
   authentication
   client