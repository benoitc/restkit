# -*- coding: utf-8 -
#
# Copyright (c) 2008, 2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
# _getCharacterEncoding from Feedparser under BSD License :
#
# Copyright (c) 2002-2006, Mark Pilgrim, All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
restclient.rest
~~~~~~~~~~~~~~~

This module provide a common interface for all HTTP equest. 

    >>> from restclient import Resource
    >>> res = Resource('http://friendpaste.com')
    >>> res.get('/5rOqE9XTz7lccLgZoQS4IP',headers={'Accept': 'application/json'})
    u'{"snippet": "hi!", "title": "", "id": "5rOqE9XTz7lccLgZoQS4IP", "language": "text", "revision": "386233396230"}'
    >>> res.status
    200
"""

import cgi
import mimetypes
import os
import StringIO
import types
import urllib

try:
    import chardet
except ImportError:
    chardet = False

from restclient.errors import *
from restclient.transport import getDefaultHTTPTransport, HTTPTransportBase
from restclient.utils import to_bytestring

__all__ = ['Resource', 'RestClient', 'url_quote', 'url_encode']

__docformat__ = 'restructuredtext en'

class Resource(object):
    """A class that can be instantiated for access to a RESTful resource, 
    including authentication. 

    It can use pycurl, urllib2, httplib2 or any interface over
    `restclient.http.HTTPClient`.

    """
    def __init__(self, uri, transport=None, headers=None):
        """Constructor for a `Resource` object.

        Resource represent an HTTP resource.

        :param uri: str, full uri to the server.
        :param transport: any http instance of object based on 
                `restclient.http.HTTPClient`. By default it will use 
                a client based on `pycurl <http://pycurl.sourceforge.net/>`_ if 
                installed or urllib2. You could also use 
                `restclient.http.HTTPLib2HTTPClient`,a client based on 
                `Httplib2 <http://code.google.com/p/httplib2/>`_ or make your
                own depending of the option you need to access to the serve
                (authentification, proxy, ....).
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        """

        self.client = RestClient(transport, headers=headers)
        self.uri = uri
        self.transport = self.client.transport 
        self._headers = headers

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.uri)

    def clone(self):
        """if you want to add a path to resource uri, you can do:

        .. code-block:: python

            resr2 = res.clone()
        
        """
        obj = self.__class__(self.uri, transport=self.transport)
        return obj
   
    def __call__(self, path):
        """if you want to add a path to resource uri, you can do:
        
        .. code-block:: python

            Resource("/path").get()
        """

        return type(self)(self.client.make_uri(self.uri, path),
                transport=self.transport)

    
    def get(self, path=None, headers=None, **params):
        """ HTTP GET         
        
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request.
        """
        return self.request("GET", path=path, headers=headers, **params)

    def delete(self, path=None, headers=None, **params):
        """ HTTP DELETE

        see GET for params description.
        """
        return self.request("DELETE", path=path, headers=headers, **params)

    def head(self, path=None, headers=None, **params):
        """ HTTP HEAD

        see GET for params description.
        """
        return self.request("HEAD", path=path, headers=headers, **params)

    def post(self, path=None, payload=None, headers=None, **params):
        """ HTTP POST

        :param payload: string passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request
        """

        return self.request("POST", path=path, payload=payload, headers=headers, **params)

    def put(self, path=None, payload=None, headers=None, **params):
        """ HTTP PUT

        see POST for params description.
        """
        return self.request("PUT", path=path, payload=payload, headers=headers, **params)

    def request(self, method, path=None, payload=None, headers=None, **params):
        """ HTTP request

        This method may be the only one you want to override when
        subclassing `restclient.rest.Resource`.
        
        :param payload: string or File object passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request
        """
        _headers = self._headers or {}
        _headers.update(headers or {})
        return self.client.request(method, self.uri, path=path,
                body=payload, headers=_headers, **params)

    def get_response(self):
        return self.client.get_response()
    response = property(get_response)

    def get_status(self):
        return self.client.status
    status = property(get_status)

    def update_uri(self, path):
        """
        to set a new uri absolute path
        """
        self.uri = self.client.make_uri(self.uri, 
                path)


class RestClient(object):
    """Basic rest client

        >>> res = RestClient()
        >>> xml = res.get('http://pypaste.com/about')
        >>> json = res.get('http://pypaste.com/3XDqQ8G83LlzVWgCeWdwru', headers={'accept': 'application/json'})
        >>> json
        u'{"snippet": "testing API.", "title": "", "id": "3XDqQ8G83LlzVWgCeWdwru", "language": "text", "revision": "363934613139"}'
    """

    charset = 'utf-8'
    encode_keys = True
    safe = "/:"

    def __init__(self, transport=None, headers=None):
        """Constructor for a `RestClient` object.

        RestClient represent an HTTP client.

        :param transport: any http instance of object based on 
                `restclient.transport.HTTPTransportBase`. By default it will use 
                a client based on `pycurl <http://pycurl.sourceforge.net/>`_ if 
                installed or `restclient.transport.HTTPLib2Transport`,a client based on 
                `Httplib2 <http://code.google.com/p/httplib2/>`_ or make your
                own depending of the option you need to access to the serve
                (authentification, proxy, ....).
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        """ 

        if transport is None:
            transport = getDefaultHTTPTransport()

        self.transport = transport

        self.status = None
        self.response = None
        self._headers = headers


    def get(self, uri, path=None, headers=None, **params):
        """ HTTP GET         
        
        :param uri: str, uri on which you make the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request.
        """

        return self.request('GET', uri, path=path, headers=headers, **params)

    def head(self, uri, path=None, headers=None, **params):
        """ HTTP HEAD

        see GET for params description.
        """
        return self.request("HEAD", uri, path=path, headers=headers, **params)

    def delete(self, uri, path=None, headers=None, **params):
        """ HTTP DELETE

        see GET for params description.
        """
        return self.request('DELETE', uri, path=path, headers=headers, **params)

    def post(self, uri, path=None, body=None, headers=None, **params):
        """ HTTP POST

        :param uri: str, uri on which you make the request
        :param body: string or File object passed to the body of the request
        :param path: string  additionnal path to the uri
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request
        """
        return self.request("POST", uri, path=path, body=body, headers=headers, **params)

    def put(self, uri, path=None, body=None, headers=None, **params):
        """ HTTP PUT

        see POST for params description.
        """

        return self.request('PUT', uri, path=path, body=body, headers=headers, **params)

    def request(self, method, uri, path=None, body=None, headers=None, **params):
        """ Perform HTTP call support GET, HEAD, POST, PUT and DELETE.
        
        Usage example, get friendpaste page :

        .. code-block:: python

            from restclient import RestClient
            client = RestClient()
            page = resource.request('GET', 'http://friendpaste.com')

        Or get a paste in JSON :

        .. code-block:: python

            from restclient import RestClient
            client = RestClient()
            client.request('GET', 'http://friendpaste.com/5rOqE9XTz7lccLgZoQS4IP'),
                headers={'Accept': 'application/json'})

        :param method: str, the HTTP action to be performed: 
            'GET', 'HEAD', 'POST', 'PUT', or 'DELETE'
        :param path: str or list, path to add to the uri
        :param data: tring or File object.
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request.
        
        :return: str.
        """

        # init headers
        _headers = self._headers or {}
        _headers.update(headers or {})
        
        is_unicode = True
        
        if body and body is not None and 'Content-Length' not in headers:
            if isinstance(body, file):
                try:
                    body.flush()
                except IOError:
                    pass
                size = int(os.fstat(body.fileno())[6])
            elif isinstance(body, types.StringTypes):
                size = len(body)
                body = to_bytestring(body)
            elif isinstance(body, dict):
                body = form_encode(body)
                size = len(body)
            else:
                raise RequestError('Unable to calculate '
                    'the length of the data parameter. Specify a value for '
                    'Content-Length')
            _headers['Content-Length'] = size
            
            if 'Content-Type' not in headers:
                type = None
                if hasattr(body, 'name'):
                    type = mimetypes.guess_type(body.name)[0]
                _headers['Content-Type'] = type and type or 'application/octet-stream'
                
        try:
            resp, data = self.transport.request(self.make_uri(uri, path, **params), 
                method=method, body=body, headers=_headers)
        except TransportError, e:
            raise RequestError(str(e))

        self.status  = status_code = resp.status
        self.response = resp
        
        
        if status_code >= 400:
            if status_code == 404:
                raise ResourceNotFound(data, http_code=404, response=resp)
            elif status_code == 401 or status_code == 403:
                raise Unauthorized(data, http_code=status_code,
                        response=resp)
            else:
                raise RequestFailed(data, http_code=status_code,
                    response=resp)

        # determine character encoding
        true_encoding, http_encoding, xml_encoding, sniffed_xml_encoding, \
        acceptable_content_type = _getCharacterEncoding(resp, data)
        

        tried_encodings = []
        # try: HTTP encoding, declared XML encoding, encoding sniffed from BOM
        for proposed_encoding in (true_encoding, xml_encoding, sniffed_xml_encoding):
            if not proposed_encoding: continue
            if proposed_encoding in tried_encodings: continue
            tried_encodings.append(proposed_encoding)
            try:
               return data.decode(proposed_encoding)
               break
            except:
                pass
                
        # if still no luck and we haven't tried utf-8 yet, try that
        if 'utf-8' not in tried_encodings:
            try:
                proposed_encoding = 'utf-8'
                tried_encodings.append(proposed_encoding)
                return data.decode(proposed_encoding)
              
            except:
                pass
                
        # if still no luck and we haven't tried windows-1252 yet, try that
        if 'windows-1252' not in tried_encodings:
            try:
                proposed_encoding = 'windows-1252'
                tried_encodings.append(proposed_encoding)
                return data.decode(proposed_encoding)
            except:
                pass
                
        # if no luck and we have auto-detection library, try that
        if chardet:
            try:
                proposed_encoding = chardet.detect(data)['encoding']
                if proposed_encoding and (proposed_encoding not in tried_encodings):
                    tried_encodings.append(proposed_encoding)
                    return data.decode(proposed_encoding)
            except:
                pass
              
        # give up, return data as is.   
        return data 

    def get_response(self):
        return self.response

    def make_uri(self, base, *path, **query):
        """Assemble a uri based on a base, any number of path segments, and query
        string parameters.

        """
        base_trailing_slash = False
        if base and base.endswith("/"):
            base_trailing_slash = True
            base = base[:-1]
        retval = [base]

        # build the path
        _path = []
        trailing_slash = False       
        for s in path:
            if s is not None and isinstance(s, basestring):
                if len(s) > 1 and s.endswith('/'):
                    trailing_slash = True
                else:
                    trailing_slash = False
                _path.append(url_quote(s.strip('/'), self.charset, self.safe))
                       
        path_str =""
        if _path:
            path_str = "/".join([''] + _path)
            if trailing_slash:
                path_str = path_str + "/" 
        elif base_trailing_slash:
            path_str = path_str + "/" 
            
        if path_str:
            retval.append(path_str)

        params = []
        for k, v in query.items():
            if type(v) in (list, tuple):
                params.extend([(k, i) for i in v if i is not None])
            elif v is not None:
                params.append((k,v))
        if params:
            retval.extend(['?', url_encode(dict(params), self.charset, self.encode_keys)])

        return ''.join(retval)


# code borrowed to Wekzeug with minor changes

def url_quote(s, charset='utf-8', safe='/:'):
    """URL encode a single string with a given encoding."""
    if isinstance(s, unicode):
        s = s.encode(charset)
    elif not isinstance(s, str):
        s = str(s)
    return urllib.quote(s, safe=safe)

def url_encode(obj, charset="utf8", encode_keys=False):
    if isinstance(obj, dict):
        items = []
        for k, v in obj.iteritems():
            if not isinstance(v, (tuple, list)):
                v = [v]
            items.append((k, v))
    else:
        items = obj or ()

    tmp = []
    for key, values in items:
        if encode_keys and isinstance(key, unicode):
            key = key.encode(charset)
        else:
            key = str(key)

        for value in values:
            if value is None:
                continue
            elif isinstance(value, unicode):
                value = value.encode(charset)
            else:
                value = str(value)
        tmp.append('%s=%s' % (urllib.quote(key),
            urllib.quote_plus(value)))

    return '&'.join(tmp)
    
def form_encode(obj, charser="utf8"):
    tmp = []
    for key, value in obj.items():
        tmp.append("%s=%s" % (url_quote(key), 
                url_quote(value)))
    return to_bytestring(";".join(tmp))



def _getCharacterEncoding(http_headers, xml_data):
    '''Get the character encoding of the XML document

    http_headers is a dictionary
    xml_data is a raw string (not Unicode)
    
    This is so much trickier than it sounds, it's not even funny.
    According to RFC 3023 ('XML Media Types'), if the HTTP Content-Type
    is application/xml, application/*+xml,
    application/xml-external-parsed-entity, or application/xml-dtd,
    the encoding given in the charset parameter of the HTTP Content-Type
    takes precedence over the encoding given in the XML prefix within the
    document, and defaults to 'utf-8' if neither are specified.  But, if
    the HTTP Content-Type is text/xml, text/*+xml, or
    text/xml-external-parsed-entity, the encoding given in the XML prefix
    within the document is ALWAYS IGNORED and only the encoding given in
    the charset parameter of the HTTP Content-Type header should be
    respected, and it defaults to 'us-ascii' if not specified.

    Furthermore, discussion on the atom-syntax mailing list with the
    author of RFC 3023 leads me to the conclusion that any document
    served with a Content-Type of text/* and no charset parameter
    must be treated as us-ascii.  (We now do this.)  And also that it
    must always be flagged as non-well-formed.  (We now do this too.)
    
    If Content-Type is unspecified (input was local file or non-HTTP source)
    or unrecognized (server just got it totally wrong), then go by the
    encoding given in the XML prefix of the document and default to
    'iso-8859-1' as per the HTTP specification (RFC 2616).
    
    Then, assuming we didn't find a character encoding in the HTTP headers
    (and the HTTP Content-type allowed us to look in the body), we need
    to sniff the first few bytes of the XML data and try to determine
    whether the encoding is ASCII-compatible.  Section F of the XML
    specification shows the way here:
    http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info

    If the sniffed encoding is not ASCII-compatible, we need to make it
    ASCII compatible so that we can sniff further into the XML declaration
    to find the encoding attribute, which will tell us the true encoding.

    Of course, none of this guarantees that we will be able to parse the
    feed in the declared character encoding (assuming it was declared
    correctly, which many are not).  CJKCodecs and iconv_codec help a lot;
    you should definitely install them if you can.
    http://cjkpython.i18n.org/
    '''

    def _parseHTTPContentType(content_type):
        '''takes HTTP Content-Type header and returns (content type, charset)

        If no charset is specified, returns (content type, '')
        If no content type is specified, returns ('', '')
        Both return parameters are guaranteed to be lowercase strings
        '''
        content_type = content_type or ''
        content_type, params = cgi.parse_header(content_type)
        return content_type, params.get('charset', '').replace("'", '')

    sniffed_xml_encoding = ''
    xml_encoding = ''
    true_encoding = ''
    http_content_type, http_encoding = _parseHTTPContentType(http_headers.get('Content-Type'))
    # Must sniff for non-ASCII-compatible character encodings before
    # searching for XML declaration.  This heuristic is defined in
    # section F of the XML specification:
    # http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info
    try:
        if xml_data[:4] == '\x4c\x6f\xa7\x94':
            # EBCDIC
            xml_data = _ebcdic_to_ascii(xml_data)
        elif xml_data[:4] == '\x00\x3c\x00\x3f':
            # UTF-16BE
            sniffed_xml_encoding = 'utf-16be'
            xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') and (xml_data[2:4] != '\x00\x00'):
            # UTF-16BE with BOM
            sniffed_xml_encoding = 'utf-16be'
            xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
        elif xml_data[:4] == '\x3c\x00\x3f\x00':
            # UTF-16LE
            sniffed_xml_encoding = 'utf-16le'
            xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and (xml_data[2:4] != '\x00\x00'):
            # UTF-16LE with BOM
            sniffed_xml_encoding = 'utf-16le'
            xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
        elif xml_data[:4] == '\x00\x00\x00\x3c':
            # UTF-32BE
            sniffed_xml_encoding = 'utf-32be'
            xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
        elif xml_data[:4] == '\x3c\x00\x00\x00':
            # UTF-32LE
            sniffed_xml_encoding = 'utf-32le'
            xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
        elif xml_data[:4] == '\x00\x00\xfe\xff':
            # UTF-32BE with BOM
            sniffed_xml_encoding = 'utf-32be'
            xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
        elif xml_data[:4] == '\xff\xfe\x00\x00':
            # UTF-32LE with BOM
            sniffed_xml_encoding = 'utf-32le'
            xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
        elif xml_data[:3] == '\xef\xbb\xbf':
            # UTF-8 with BOM
            sniffed_xml_encoding = 'utf-8'
            xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
        else:
            # ASCII-compatible
            pass
        xml_encoding_match = re.compile('^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
    except:
        xml_encoding_match = None
    if xml_encoding_match:
        xml_encoding = xml_encoding_match.groups()[0].lower()
        if sniffed_xml_encoding and (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode', 'iso-10646-ucs-4', 'ucs-4', 'csucs4', 'utf-16', 'utf-32', 'utf_16', 'utf_32', 'utf16', 'u16')):
            xml_encoding = sniffed_xml_encoding
    acceptable_content_type = 0
    application_content_types = ('application/xml', 'application/xml-dtd', 'application/xml-external-parsed-entity')
    text_content_types = ('text/xml', 'text/xml-external-parsed-entity')
    if (http_content_type in application_content_types) or \
       (http_content_type.startswith('application/') and http_content_type.endswith('+xml')):
        acceptable_content_type = 1
        true_encoding = http_encoding or xml_encoding or 'utf-8'
    elif (http_content_type in text_content_types) or \
         (http_content_type.startswith('text/')) and http_content_type.endswith('+xml'):
        acceptable_content_type = 1
        true_encoding = http_encoding or 'us-ascii'
    elif http_content_type.startswith('text/'):
        true_encoding = http_encoding or 'us-ascii'
    elif http_headers and (not http_headers.has_key('content-type')):
        true_encoding = xml_encoding or 'iso-8859-1'
    else:
        true_encoding = xml_encoding or 'utf-8'
    return true_encoding, http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type