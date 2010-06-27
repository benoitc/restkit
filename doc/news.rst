.. _news:

News
====

2.0 / 2010-06-28
----------------

- Complete refactoring of pool. Now handle more concurrent connections (priority to read)

- Added full ssl support in restkit. It needs `ssl <http://pypi.python.org/pypi/ssl>`_ module on Python 2.5x
- New HTTP parser.
- Added close method to response object to make sure the socket is correctly released.
- Improved default http client, so form objects can be directly handled.
- Improved request function


Breaking changes:
+++++++++++++++++

- **Default HttpResponse isn't any more persistent**. You have to save it to reuse it. A persistent response will be provided in restkit 2.1 .
- Deprecate HttpResponse body, unicode_body and body_file properties. They are replaced  by body_string and body_stream methods.
- Resource arguments
- Complete refactoring of filters. Now they have to be declared when you create a resource or http client. An on_connect method can be used in filter now. This method is used before the connection happen, it's useful for proxy support for example. 
- Oauth2 filter has been simplfied, see `example <authentication.html>`_ 

1.3.1 / 2010-04-09
------------------

- Fixed Python 2.5 compatibility for ssl connections

1.3 / 2010-04-02
----------------

- Added IPython shell extension (`restkit --shell`)
- fix Python 2.5 compatibility
- fix Eventlet and Gevent spools extensions
- By default accept all methods in proxy

1.2.1 / 2010-03-08
------------------

- Improve console client

1.2 / 2010-03-06
------------------------

- Added `GEvent <pool.html>`_ Support
- Added `wsgi_proxy <wsgi_proxy.html>`_ using webob and restkit
- Improved pool management
- Make HTTP parsing faster.
- Fix TeeInput


1.1.3 / 2010-03-04
------------------

- Fix ssl connections

1.1.2 / 2010-03-02
------------------

- More logging information
- Fix retry loop so an error is raised instead of returning None.

1.1 / 2010-03-01
----------------

- Improved HTTP Parser - Now buffered.
- Logging facility

1.0 / 2010-02-28
----------------

- New HTTP Parser and major refactoring
- Added OAuth support
- Added HTTP Filter
- Added support of chunked encoding
- Removed `rest.RestClient`
- Add Connection pool working with Eventlet 0.9.6
