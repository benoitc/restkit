.. _basic_authentication:

Basic authentication
====================

Basic authentication is managed by the object :api:`restkit.filters.BasicAuth`. It's handled automatically in :api:`restkit.request` function and in :api:`restkit.resource.Resource` object if `basic_auth_url` property is True.

To use `basic authentication` in a `Resource object` you can do::

  from restkit import Resource, BasicAuth
 
  auth = BasicAuth("username", "password")
  r = Resource("http://friendpaste.com", filters=[auth])
 
Or simply use an authentication url::

  r = Resource("http://username:password@friendpaste.com")