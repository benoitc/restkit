# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import mimetypes
import os
import re
import urllib


from restkit.util import to_bytestring, url_quote

MIME_BOUNDARY = 'END_OF_PART'

def form_encode(obj, charser="utf8"):
    tmp = []
    for key, value in obj.items():
        tmp.append("%s=%s" % (url_quote(key), 
                url_quote(value)))
    return to_bytestring("&".join(tmp))


class BoundaryItem(object):
    def __init__(self, name, value, fname=None, filetype=None, filesize=None):
        self.name = url_quote(name)
        if value is not None and not hasattr(value, 'read'):
            value = url_quote(value)
            self.size = len(value)
        self.value = value
        if fname is not None:
            if isinstance(fname, unicode):
                fname = fname.encode("utf-8").encode("string_escape").replace('"', '\\"')
            else:
                fname = fname.encode("string_escape").replace('"', '\\"')
        self.fname = fname
        if filetype is not None:
            filetype = to_bytestring(filetype)
        self.filetype = filetype
        
        if isinstance(value, file) and filesize is None:
            try:
                value.flush()
            except IOError:
                pass
            self.size = int(os.fstat(value.fileno())[6])
            
    def encode_hdr(self, boundary):
        """Returns the header of the encoding of this parameter"""
        boundary = url_quote(boundary)
        headers = ["--%s" % boundary]
        if self.fname:
            disposition = 'form-data; name="%s"; filename="%s"' % (self.name,
                    self.fname)
        else:
            disposition = 'form-data; name="%s"' % self.name
        headers.append("Content-Disposition: %s" % disposition)
        if self.filetype:
            filetype = self.filetype
        else:
            filetype = "text/plain; charset=utf-8"
        headers.append("Content-Type: %s" % filetype)
        headers.append("Content-Length: %i" % self.size)
        headers.append("")
        headers.append("")
        return "\r\n".join(headers)

    def encode(self, boundary):
        """Returns the string encoding of this parameter"""
        value = self.value
        if re.search("^--%s$" % re.escape(boundary), value, re.M):
            raise ValueError("boundary found in encoded string")

        return "%s%s\r\n" % (self.encode_hdr(boundary), value)
        
    def iter_encode(self, boundary, blocksize=16384):
        if not hasattr(self.value, "read"):
            yield self.encode(boundary)
        else:
            yield self.encode_hdr(boundary)
            while True:
                block = self.value.read(blocksize)
                if not block:
                    yield "\r\n"
                    break
                yield block
                
                
class MultipartForm(object):
    
    def __init__(self, params, boundary, headers):
        self.boundary = boundary
        self.boundaries = []
        self.size = 0
        
        self.content_length = headers.get('Content-Length')
        
        if hasattr(params, 'items'):
            params = params.items()
            
        for param in params:
            name, value = param
            if hasattr(value, "read"):
                fname = getattr(value, 'name')
                if fname is not None:
                    filetype = ';'.join(filter(None, mimetypes.guess_type(fname)))
                else:
                    filetype = None
                if not isinstance(value, file) and self.content_length is None:
                    value = value.read()
                    
                boundary = BoundaryItem(name, value, fname, filetype)
            else:
                 boundary = BoundaryItem(name, value)
            self.boundaries.append(boundary)

    def get_size(self):
        if self.content_length is not None:
            return int(self.content_length)
        size = 0
        for boundary in self.boundaries:
            size = size + boundary.size
        return size
        
    def __iter__(self):
        for boundary in self.boundaries:
            for block in boundary.iter_encode(self.boundary):
                yield block
        yield "--%s--\r\n" % self.boundary
                    

def multipart_form_encode(params, headers, boundary):
    headers = headers or {}
    boundary = urllib.quote_plus(boundary)
    body = MultipartForm(params, boundary, headers)
    headers['Content-Type'] = "multipart/form-data; boundary=%s" % boundary
    headers['Content-Length'] = str(body.get_size())
    return body, headers