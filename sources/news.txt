.. _news:

News
====

4.1.0 / 2012-01-31
------------------

- fix connection reusing. When connection is closed or an EPIPE/EAGAIN
  error happen, we now retry it.
- fix wgsi_proxy contrib
- fix examples

4.0.0 / 2012-01-25
------------------

- Replace the socket pool by `socketpool
  <https://github.com/benoitc/socketpool>`_ improve connection handling
  and better management of gevent & eventlet.
- Fix NoMoreData issue
- Fix SSL connections
- multipart forms: quote is now configurable & flush size cache


3.3.1 / 2011-09-18
------------------

- Add `hook <https://github.com/benoitc/restkit/commit/eb90afd661e126966e948c6e780199269fd7bdfc>`_ for BoundaryItem subclasses to handle unreadable values
- Add realm support to restkit
- Fix restcli --shell, upgrade it for IPython 0.11
- Stop catching KeyboardInterrupt and SystemExit exceptions
- Make sure we don't release the socket twice

3.3.0 / 2011-06-20
------------------

- New HTTP parser, using python `http-parser <https://github.com/benoitc/http-parser>`_ 
  in C based on  http-parser from Ryan Dahl.
- Fix UnboundLocalError
- Sync oauth with last python-oauth2 (fix POST & encoding issues)
- Improve sending

Breaking changes:
+++++++++++++++++

- Headers is an IOrderdDict object now, wich means by default you can
  get any headers case insensitively using get or headers[key], as a
  result the method **iget** has been removed.

3.2.1 / 2011-03-22
------------------

- Fix sending on linux.

3.2 / 2011-02-18
----------------

- Some deep rewrite of the client. Requests and Connections are now
  maintened in their own instances, so we don't rely on client instance
  to close or release the connection Also we don't pass local variable
  to handle a request. At the end each requests are more isolated and we are
  fully threadsafe.
- Improve error report.
- Handle case where the connection is closed but the OS still accept
  sending. From the man: "When  the message does not fit into the send 
  buffer of the socket, send() normally blocks, unless th socket has 
  been placed in nonblocking I/O mode.""" . Spotted by loftus on irc.
  Thanks.

Breaking changes:
+++++++++++++++++

- Rewrite filters handling. We now pass a request instance to the
  on_request filters. If a request filter return a response, we stop to
  perform here. response filters accept now the response and request
  instances as arguments. There is no more on_connect filters (it was a
  bad idea)
- Proxy support. Proxies are now supported by passing the argument
  "use_proxy=True" to client, request and resources objects.

3.0 / 2011-02-02
----------------

- New Connection management: Better concurrency handling and iddle
  connections are now closed after a time.
- Improved Client.
- Fix redirect 
- Better error handling
- Timeout can now be set on each request.
- Major refactoring. consolidation of some module, ease the HTTP parser
  code.
- Fix timeout errors.

2.3.0 / 2010-11-25
------------------
 - Refactored Http Connections management (reuse connections).
   restkit.pool is now replaced by restkit.conn module. SimplePool has
   been replaced by TConnectionManager (threadsafe). Now by default all
   connections are reusing connections using TConnectionManager (10
   connections per route).
 - Improved Gevent & Eventlet support
 - Added an ``decompress`` option to ``request`` function and ``Resource`` 
   instance to decompress the body or not. By default it's true.
 - Added ``params_dict`` to keywords arguments of ``Resource`` instances
   methods. Allows you to pass any argument to the query. 
 - Fix response 100-continue
 - Fix compressed atatchments
 - Fix body readline
 - Fix basic authentication
 - Stop when system exit or keyboard interrupt
 - Fix oauth2

More details `here <https://github.com/benoitc/restkit/compare/2.1.1...2.1.3>`_ .

2.2.1 / 2010-09-18
------------------
 - Fix readline `b7365155 <http://github.com/benoitc/restkit/commit/b7365155168cc9df7e48edabad79b2c478e8c5c7>`_ .

2.2.0 / 2010-09-14
------------------
 - Refactor client code. Improve header parsing
 - Fix Deflate/Gzip decompression and make it fully
   streamed.
 - Fix oauth2 in POST requests
 - Fix import with Python 2.5/2.4
 - Fix Exceptions
 - body, unicod_body and body_file methods have been removed from the
   HTTP response.

2.1.6 / 2010-09-
-----------------
 - Fix debian packaging 
 - Fix oauth

2.1.4 / 2008-08-11
------------------

 - Improve HTTP parsing (backport from Gunicorn)
 - Handle KeyboardInterrupt and SystemExit exceptions in client.

2.1.3 / 2008-08-11
------------------

 - Repackaged due to a spurious print.

2.1.2 / 2008-08-11
------------------

- `Fix<http://github.com/benoitc/restkit/commit/c176f2905c82b33a69e73ab63ac91784f6d7af08>` a nasty bug in BasicAuth

2.1.1/ 2010-08-05
-----------------

- Fix clone and __call__, make sure we use original client_opts rather
  than an instance

2.1.0 / 2010-07-24
------------------

- Added make_params, make_headers method to the Resource allowing you to modify headers and params
- Added unauthorized method to Resource allowing you to react on 401/403, return True
  by default
- make sure default pool is only set one time in the main thread in
  Resource object
- Added Resouce.close() method: close the pool connections
- Added Pool.close() method: clear the pool and stop monitoring
- Updated Oauth2 module
- Handle ECONNRESET error in HTTP client
- Fix keep-alive handling
- Fix Content-Type headerfor GET
- Fix "Accept-Encoding" header
- Fix HttpResponse.close() method
- Make sure we use ssl when https scheme is used
- Fix "__call__" and clone() methods from restkit.Resource object.

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
