restkit shell
=============

restkit come with a IPython based shell to help you to debug your http apps. Just run::

    $ restkit --shell http://benoitc.github.com/restkit/

HTTP Methods
------------
::
    >>> delete([req|url|path_info])                                 # send a HTTP delete
    >>> get([req|url|path_info], **query_string)                    # send a HTTP get
    >>> head([req|url|path_info], **query_string)                   # send a HTTP head
    >>> post([req|url|path_info], [Stream()|**query_string_body])   # send a HTTP post
    >>> put([req|url|path_info], stream)                            # send a HTTP put


Helpers
-------
::

    >>> req    # request to play with. By default http methods will use this one
    <Request at 0x18fdb70 GET http://benoitc.github.com/restkit/>

    >>> stream # Stream() instance if you specified a -i in command line
    None

    >>> ctypes # Content-Types helper with headers properties
    <ContentTypes(['application_atom_xml', 'application_json',
    'application_rss_xml', 'application_xhtml_xml', 'application_xml',
    'application_xsl_xml', 'application_xslt_xml', 'image_svg_xml',
    'text_html', 'text_xml'])>

    restkit shell 1.2.1
    1) restcli$    


Here is a sample session::

    1) restcli$ req
    ----------> req()
    GET /restkit/ HTTP/1.0
    Host: benoitc.github.com
    2) restcli$ get()
    200 OK
    Content-Length: 10476
    Accept-Ranges: bytes
    Expires: Sat, 03 Apr 2010 12:25:09 GMT
    Server: nginx/0.7.61
    Last-Modified: Mon, 08 Mar 2010 07:53:16 GMT
    Connection: keep-alive
    Cache-Control: max-age=86400
    Date: Fri, 02 Apr 2010 12:25:09 GMT
    Content-Type: text/html
             2) <Response at 0x19333b0 200 OK>
    3) restcli$ resp.status
             3) '200 OK'
    4) restcli$ put()
    405 Not Allowed
    Date: Fri, 02 Apr 2010 12:25:28 GMT
    Content-Length: 173
    Content-Type: text/html
    Connection: keep-alive
    Server: nginx/0.7.61

    <html>
    <head><title>405 Not Allowed</title></head>
    <body bgcolor="white">
    <center><h1>405 Not Allowed</h1></center>
    <hr><center>nginx/0.7.61</center>
    </body>
    </html>

    4) <Response at 0x1933330 405 Not Allowed>
    5) restcli$ resp.status
             5) '405 Not Allowed'
    6) restcli$ req.path_info = '/restkit/api/index.html'
    7) restcli$ get
    ----------> get()
    200 OK
    Content-Length: 10476
    Accept-Ranges: bytes
    Expires: Sat, 03 Apr 2010 12:26:18 GMT
    Server: nginx/0.7.61
    Last-Modified: Mon, 08 Mar 2010 07:53:16 GMT
    Connection: keep-alive
    Cache-Control: max-age=86400
    Date: Fri, 02 Apr 2010 12:26:18 GMT
    Content-Type: text/html
             7) <Response at 0x19300f0 200 OK>
    8) restcli$ get('/restkit')
    301 Moved Permanently
    Location: http://benoitc.github.com/restkit/

    <html>
    <head><title>301 Moved Permanently</title></head>
    <body bgcolor="white">
    <center><h1>301 Moved Permanently</h1></center>
    <hr><center>nginx/0.7.61</center>
    </body>
    </html>

    8) <Response at 0x1930410 301 Moved Permanently>
    9) restcli$ resp.location
    9) 'http://benoitc.github.com/restkit/'

