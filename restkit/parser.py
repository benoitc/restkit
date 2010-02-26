# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import urlparse

from restkit.errors import BadStatusLine, ParserError
from restkit.util import normalize_name

class Parser(object):

    def __init__(self, ptype='response', should_close=False):
        self.status_line = ""
        self.status_int = None
        self.reason = ""
        self.status = ""
        self.headers = []
        self.headers_dict = {}
        self.raw_version = "HTTP/1.0"
        self.raw_path = ""
        self.version = (1,0)
        self.method = ""
        self.path = ""
        self.query_string = ""
        self.fragment = ""
        self._content_len = None
        self.start_offset = 0
        self.chunk_size = 0
        self._chunk_eof = False
        self.type = ptype
        self._should_close = should_close
        
    @classmethod
    def parse_response(cls, should_close=False):
        return cls(should_close=should_close)
        
    @classmethod
    def parse_request(cls):
        return cls(ptype='request')
        
    def filter_headers(self, headers, buf):
        """ take a string as buffer and an header dict 
        (empty or not). It return new position or -1 
        if parsing isn't done. headers dict is updated
        with new headers.
        """
        
        ld = len("\r\n\r\n")
        i = buf.find("\r\n\r\n")
        if i != -1:
            if i > 0:
                r = buf[:i]
            pos = i+ld
            return self.finalize_headers(headers, r, pos)
        return -1
        
    def finalize_headers(self, headers, headers_str, pos):
        """ parse the headers """
        lines = headers_str.split("\r\n")
                
        # parse first line of headers
        self._first_line(lines.pop(0))
        
        # parse headers. We silently ignore 
        # bad headers' lines
        
        _headers = {}
        hname = ""
        for line in lines:
            if line == "\t":
                headers[hname] += line.strip()
            else:
                try:
                    hname =self._parse_headerl(_headers, line)
                except ValueError: 
                    # bad headers
                    pass
        self.headers_dict = _headers
        headers.extend(list(_headers.items()))
        self.headers = headers
        self._content_len = int(_headers.get('Content-Length',0))
        
        if self.type == 'request':
            (_, _, self.path, self.query_string, self.fragment) = \
                urlparse.urlsplit(self.raw_path)
        return pos
    
    def parse_status(self, status):
        try:
            try:
                self.status_int, self.reason = self.status.split(" ", 1)
            except ValueError:
                self.status_int =  self.status
            self.status_int = int(self.status_int)
        except ValueError:
            raise BadStatusLine("can't find status code")       
        
    def _first_line(self, line):
        """ parse first line """
        self.status_line = status_line = line.strip()
        
        try:
            if self.type == 'response':
                version, self.status = status_line.split(" ", 1)
            else:
                method, path, version = status_line.split(" ")
        except ValueError:
            return
  
        version = version.strip()
        self.raw_version = version
        try:
            major, minor = version.split("HTTP/")[1].split(".")
            version = (int(major), int(minor))
        except IndexError:
            version = (1, 0)

        self.version = version
        if self.type == 'response':
            try:
                try:
                    self.status_int, self.reason = self.status.split(" ", 1)
                except ValueError:
                    self.status_int =  self.status
                self.status_int = int(self.status_int)
            except ValueError:
                raise BadStatusLine("can't find status code")
        else:    
            self.method = method.upper()
            self.raw_path = path
        
    def _parse_headerl(self, hdrs, line):
        """ parse header line"""
        name, value = line.split(":", 1)
        name = normalize_name(name.strip())
        value = value.rsplit("\r\n",1)[0].strip()
        if name in hdrs:
            hdrs[name] = "%s, %s" % (hdrs[name], value)
        else:
            hdrs[name] = value
        return name
      
    @property
    def should_close(self):
        if self._should_close:
            return True
        elif self.headers_dict.get("Connection") == "close":
            return True
        elif self.headers_dict.get("Connection") == "Keep-Alive":
            return False
        elif self.version <= (1, 0):
            return True
        return False
        
    @property
    def is_chunked(self):
        """ is TE: chunked ?"""
        transfert_encoding = self.headers_dict.get('Transfer-Encoding')
        return (transfert_encoding == "chunked")
        
    @property
    def content_len(self):
        """ return content length as integer or
        None."""
        transfert_encoding = self.headers_dict.get('Transfer-Encoding')
        content_length = self.headers_dict.get('Content-Length')
        if transfert_encoding != "chunked":
            if content_length is None:
                return 0
            return int(content_length)
        else:
            return None
            
    def body_eof(self):
        """do we have all the body ?"""
        if self.is_chunked:
            if self._chunk_eof:
                return True
        elif self._content_len == 0:
            return True
        return False
        
    def read_chunk(self, data):
        if not self.start_offset:
            i = data.find("\r\n")
            if i != -1:
                chunk = data[:i].strip().split(";", 1)
                chunk_size = int(chunk.pop(0), 16)
                self.start_offset = i+2
                self.chunk_size = chunk_size
                
        if self.start_offset:
            if self.chunk_size == 0:
                self._chunk_eof = True
                ret = '', data[:self.start_offset]
                return ret
            else:
                buf = data[self.start_offset:self.start_offset+self.chunk_size]
                end_offset = self.start_offset + self.chunk_size + 2
                # we wait CRLF else return None
                if len(data) >= end_offset:
                    ret = buf, data[end_offset:]
                    self.chunk_size = 0
                    return ret

        return '', data
        
    def trailing_header(self, data):
        i = data.find("\r\n\r\n")
        return i
        
    def filter_body(self, data):
        """
        Filter body and return a tuple: (body_chunk, new_buffer)
        Both can be None, and new_buffer is always None if its empty.
        """
        dlen = len(data)
        chunk = ''
        if self.is_chunked:
            try:
                chunk, data = self.read_chunk(data)
            except Exception, e:
                raise ParserError("chunked decoding error [%s]" % str(e))
                
            if not chunk:
                return '', data
        else:
            if self._content_len > 0:
                nr = min(dlen, self._content_len)
                chunk = data[:nr]
                self._content_len -= nr
                data = ''
                
        self.start_offset = 0
        return (chunk, data)
