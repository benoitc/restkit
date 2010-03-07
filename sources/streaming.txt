Stream you content
==================

With Restkit you can easily stream your content to an from a server. 

Stream to
---------

To stream a content to a server, pass to your request a file (or file-like object) or an iterator as `payload`. If you use an iterator or a file-like object and Restkit can't determine its size (by reading `Content-Length` header or fetching the size of the file), sending will be chunked and Restkit add `Transfer-Encoding: chunked` header to the list of headers.

Here is a quick snippet with a file::

  from restkit import request
  
  with open("/some/file", "r") as f:
    request("/some/url", 'POST', payload=f)
    
Here restkit will put the file size in `Content-Length` header.  Another example with an iterator::

  from restkit import request
  
  myiterator = ['line 1', 'line 2']
  request("/some/url", 'POST', payload=myiterator)

Sending will be chunked. If you want to send without TE: chunked, you need to add the `Content-Length` header::

  request("/some/url", 'POST', payload=myiterator, 
      headers={'content-Length': 12})
      
Stream from
-----------

Each requests return a :api:`restkit.client.HttpResponse` object. If you want to receive the content in a streaming fashion you just have to use the `body_file` member of the response. You can `iter` on it or just use as a file-like object (read, readline, readlines, ...). Big upload are saved as a temporary file in the filesystem, while upload <= 1Mo are in memory. You can reuse the response at any moment.

Quick snippet with iteration::

  import os
  from restkit import request
  import tempfile
  
  r = request("http://e-engura.com/images/logo.gif")
  fd, fname = tempfile.mkstemp(suffix='.gif')
  with os.fdopen(fd, "wb") as f:
      for block in r.body_file:
          f.write(block)
      
Or if you just want to read::

  with os.fdopen(fd, "wb") as f:
      while True:
          data = r.body_file.read(1024)
          if not data:
              break
          f.write(data)