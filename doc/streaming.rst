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

Each requests return a :api:`restkit.client.HttpResponse` object. If you want to receive the content in a streaming fashion you just have to use the `body_stream` member of the response. You can `iter` on it or just use as a file-like object (read, readline, readlines, ...).

**Attention**: Since 2.0, response.body are just streamed and aren't persistent. In previous version, the implementation may cause problem with memory or storage usage.

Quick snippet with iteration::

  import os
  from restkit import request
  import tempfile
  
  r = request("http://e-engura.com/images/logo.gif")
  fd, fname = tempfile.mkstemp(suffix='.gif')
  
  with r.body_stream() as body:
    with os.fdopen(fd, "wb") as f:
      for block in body:
          f.write(block)
      
Or if you just want to read::

  with r.body_stream() as body:
    with os.fdopen(fd, "wb") as f:
      while True:
          data = body.read(1024)
          if not data:
              break
          f.write(data)

Tee input
---------

While with body_stream you can only consume the input until the end, you
may want to reuse this body later in your application. For that, restkit
since the 3.0 version offer the `tee` method. It copy response input to 
standard output or a file if length > sock.MAX_BODY. When all the input 
has been read, connection is released::

   from restkit import request
   import tempfile

   r = request("http://e-engura.com/images/logo.gif")
   fd, fname = tempfile.mkstemp(suffix='.gif')
   fd1, fname1 = tempfile.mkstemp(suffix='.gif')
   
   body = t.tee()
   # save first file
   with os.fdopen(fd, "wb") as f:
      for chunk in body: f.write(chunk)

   # reset
   body.seek(0)
   # save second file.
   with os.fdopen(fd1, "wb") as f:
      for chunk in body: f.write(chunk)


