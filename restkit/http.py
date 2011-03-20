# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import os
import re
import sys
import urlparse
import zlib

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from .datastructures import MultiDict
from .errors import NoMoreData, ChunkMissingTerminator, \
InvalidChunkSize, InvalidRequestLine, InvalidHTTPVersion, \
InvalidHTTPStatus, InvalidHeader, InvalidHeaderName, HeaderLimit

MAXAMOUNT = 1048576

        
class ChunkedReader(object):
    def __init__(self, req, fp):
        self.fp = fp
        self.req = req
        self.buf = StringIO()
        self.chunk_left = None

    def read(self, size):
        if self.fp is None:
            return ''

        chunk_left = self.chunk_left
        value = []
        while True:
            if chunk_left is None:
                line = self.fp.readline()
                i = line.find(';')
                if i >= 0:
                    line = line[:i] # strip chunk-extensions
                try:
                    chunk_left = int(line, 16)
                except ValueError:
                    # close the connection as protocol synchronisation is
                    # probably lost
                    self.close()
                    raise NoMoreData(''.join(value))
                if chunk_left == 0:
                    break
            if size is None:
                value.append(self._read(chunk_left))
            elif size < chunk_left:
                value.append(self._read(size))
                self.chunk_left = chunk_left - size
                return ''.join(value)
            elif size == chunk_left:
                value.append(self._read(size))
                self._read(2)  # toss the CRLF at the end of the chunk
                self.chunk_left = None
                return ''.join(value)
            else:
                value.append(self._read(chunk_left))
                size -= chunk_left

            # we read the whole chunk, get another
            self._read(2)      # toss the CRLF at the end of the chunk
            chunk_left = None

        # read and discard trailer up to the CRLF terminator
        ### note: we shouldn't have any trailers!
        while True:
            line = self.fp.readline()
            if not line:
                # a vanishingly small number of sites EOF without
                # sending the trailer
                break
            if line == '\r\n':
                break

        # we read everything; close the "file"
        self.close()

        return ''.join(value)

    def _read(self, size):
        s = []
        while size > 0:
            chunk = self.fp.read(min(size, MAXAMOUNT))
            if not chunk:
                raise NoMoreData(''.join(s))
            s.append(chunk)
            size -= len(chunk)
        return ''.join(s)

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None

class LengthReader(object):
    def __init__(self, req, fp, length):
        self.req = req
        self.fp = fp
        self.length = length

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None

    
    def read(self, size=None):
        if self.fp is None:
            return ''

        if size is None:
            size = self.length
            s = []
            while size > 0:
                chunk = self.fp.read(min(size, MAXAMOUNT))
                if not chunk:
                    raise NoMoreData(''.join(s))
                s.append(chunk)
                size -= len(chunk)
            self.close()
            return ''.join(s)

        if not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")

        size = min(self.length, size)
        if size < 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return ""    

        s = self.fp.read(size)
        self.length -= len(s)
        if not self.length:
            self.close() 

        return s


class EOFReader(object):
    def __init__(self, req, fp):
        self.req = req
        self.fp = fp
        print "ici"

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None

    def read(self, size=None):
        if not self.fp:
            return ''

        if size is None:
            s = self.fp.read()
            self.close()
            return s

        if not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")
        if size < 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return ""

        s = self.fp.read(min(size, sys.maxint))
        if not s:
            self.fp.close()
            self.fp = None

        return s
        
class Body(object):
    def __init__(self, reader):
        self.reader = reader
        self.buf = StringIO()
        self.closed = False
            
    def __iter__(self):
        return self
    
    def next(self):
        ret = self.readline()
        if not ret:
            raise StopIteration()
        return ret

    def discard(self):
        self.read()

    def getsize(self, size):
        if size is None:
            return sys.maxint
        elif not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")
        elif size < 0:
            return sys.maxint
        return size
    
    def read(self, size=None):
        return self.reader.read(size)

    def readline(self, size=None):
        size = self.getsize(size)
        if size == 0:
            return ""
        
        buf = []
        lsize = 0 
        while lsize < size:
            ch = self.reader.read(1)
            if not len(ch):
                self.closed = True
                break

            if ch == "\n":
                break
            lsize += 1
            buf.append(ch)
        return "".join(buf)
    
    def readlines(self, size=None):
        ret = []
        data = self.read()
        while len(data):
            pos = data.find("\n")
            if pos < 0:
                ret.append(data)
                data = ""
            else:
                line, data = data[:pos+1], data[pos+1:]
                ret.append(line)
        return ret
        

class GzipBody(Body):
    def __init__(self, reader):
        super(GzipBody, self).__init__(reader)
        self._d = zlib.decompressobj(16+zlib.MAX_WBITS)
        
    def _decompress(self, data):
        return self._d.decompress(data) 
        
    def read(self, size=None):
        size = self.getsize(size)
        if size == 0:
            return ""

        if size < self.buf.tell():
            data = self.buf.getvalue()
            ret, rest = data[:size], data[size:]
            self.buf.truncate(0)
            self.buf.write(rest)
            return self._decompress(ret)

        while size > self.buf.tell():
            data = self.reader.read(1024)
            if not len(data):
                break
            self.buf.write(data)

        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf.truncate(0)
        self.buf.write(rest)
        return self._decompress(ret)
    
    def readline(self, size=None):
        size = self.getsize(size)
        if size == 0:
            return ""
        
        idx = self.buf.getvalue().find("\n")
        while idx < 0:
            data = self.reader.read(1024)
            if not len(data):
                break
            self.buf.write(self._decompress(data))
            idx = self.buf.getvalue().find("\n")
            if size < self.buf.tell():
                break
        
        # If we didn't find it, and we got here, we've
        # exceeded size or run out of data.
        if idx < 0:
            rlen = min(size, self.buf.tell())
        else:
            rlen = idx + 1

            # If rlen is beyond our size threshold, trim back
            if rlen > size:
                rlen = size
        
        data = self.buf.getvalue()
        ret, rest = data[:rlen], data[rlen:]
        
        self.buf.truncate(0)
        self.buf.write(rest)
        return ret


class DeflateBody(GzipBody):
    def __init__(self, reader):
        super(DeflateBody, self).__init__(reader)
        self._d = zlib.decompressobj()


class Request(object):
    def __init__(self, conn, decompress=True,
            max_status_line_garbage=None,
            max_header_count=0):
        self.fp = conn.makefile("rb")

        self.version = None
        self.headers = MultiDict() 
        self.trailers = []
        self.body = None
        self.encoding = None
        self.status = None
        self.reason = None
        self.status_int = None
        self.decompress = decompress

        if max_status_line_garbage is None:
            max_status_line_garbage = sys.maxint
        self.max_status_line_garbage=max_status_line_garbage

        self.max_header_count=max_header_count

        self.versre = re.compile("HTTP/(\d+).(\d+)")
        self.stare = re.compile("(\d{3})\s*(\w*)")
        self.hdrre = re.compile("[\x00-\x1F\x7F()<>@,;:\[\]={} \t\\\\\"]")

        self.parse()
        self.set_body_reader()
        
    
    def parse(self):
        # Parse request first line
        # With HTTP/1.1 persistent connections, the problem arises 
        # that broken scripts could return a wrong Content-Length 
        # (there are more bytes sent than specified). Unfortunately,
        # in some cases, this cannot be detected after the bad response,
        # but only before the next one. So w retry to read the line
        # until we go over max_status_line_garbage tries.
        tries = 0
        while True:
            try:
                self.parse_first_line(self.fp.readline())
                break
            except (InvalidRequestLine, InvalidHTTPVersion,
                    InvalidHTTPStatus), e:
                if tries > self.max_status_line_garbage:
                    raise InvalidRequestLine("Status line not found %s"
                            % str(e))

            # increase number of tries
            tries += 1
               
        headers = []
        while True:
            line = self.fp.readline()
            if line in ('\r\n', '\n', ''):
                break
            headers.append(line)

        self.headers = self.parse_headers(headers)
    
    def parse_first_line(self, line):
        bits = line.rstrip().split(None, 1)
        if len(bits) != 2:
            raise InvalidRequestLine(line)
            
        # version 
        matchv = self.versre.match(bits[0])
        if matchv is None:
            raise InvalidHTTPVersion(bits[0])
        self.version = (int(matchv.group(1)), int(matchv.group(2)))
            
        # status
        matchs = self.stare.match(bits[1])
        if matchs is None:
            raise InvalidHTTPStatus(bits[1])
        
        self.status = bits[1]
        self.status_int = int(matchs.group(1))
        self.reason = matchs.group(2)

    def parse_headers(self, lines):
        headers = MultiDict()

        # Parse headers into key/value pairs paying attention
        # to continuation lines.
        hdr_count = 0
        while len(lines):
            if self.max_header_count and \
                    hdr_count > self.max_header_count:

                raise HeaderLimit(self.max_header_count)

            # Parse initial header name : value pair.
            curr = lines.pop(0)
            if curr.find(":") < 0:
                raise InvalidHeader(curr.strip())
            name, value = curr.split(":", 1)
            name = name.rstrip(" \t")
            if self.hdrre.search(name.upper()):
                raise InvalidHeaderName(name)
            name, value = name.strip(), [value.lstrip()]
            
            # Consume value continuation lines
            while len(lines) and lines[0].startswith((" ", "\t")):
                value.append(lines.pop(0))
            value = ''.join(value).rstrip()
            
            headers.add(name, value)
            hdr_count += 1

        return headers

    def set_body_reader(self):
        clen = self.headers.iget('content-length')
        te = self.headers.iget('transfer-encoding')
        encoding = self.headers.iget('content-encoding')

        chunked = False
        clength = None
        if clen is not None:
            try:
                clength = int(clen)
            except ValueError:
                pass
        elif te is not None:
            chunked = te.lower() == "chunked"

        if encoding:
            self.encoding = encoding.lower()

        if chunked:
            reader = ChunkedReader(self, self.fp)
        elif clength is not None:
            reader = LengthReader(self, self.fp, clength)
        else:
            reader = EOFReader(self, self.fp)

        if self.decompress and self.encoding in ('gzip', 'deflate',):
            if self.encoding == "gzip":
                self.body =  GzipBody(reader)
            else:
                self.body = DeflateBody(reader)
        else:
            self.body = Body(reader)

    def should_close(self):
        connection = self.headers.iget("connection")

        if connection is not None:
            if connection.lower().strip() == "close":
                return True
            elif connection.lower().strip() == "keep-alive":
                return False
        return self.version <= (1, 0)

