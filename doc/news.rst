.. _news:

News
====

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
