.. _news:

News
====
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
