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
from .errors import *


class Unreader(object):
    def __init__(self, sock, max_chunk=8192):
        self.buf = StringIO()
        self.sock = sock
        self.max_chunk = max_chunk

    def _data(self):
        return self.sock.recv(self.max_chunk)
    
    def read(self, size=None):
        if size is not None and not isinstance(size, (int, long)):
            raise TypeError("size parameter must be an int or long.")
        if size == 0:
            return ""
        if size < 0:
            size = None

        self.buf.seek(0, os.SEEK_END)

        if size is None and self.buf.tell():
            ret = self.buf.getvalue()
            self.buf.truncate(0)
            return ret
        if size is None:
            return self._data()

        while self.buf.tell() < size:
            data = self._data()
            if not len(data):
                ret = self.buf.getvalue()
                self.buf.truncate(0)
                return ret
            self.buf.write(data)

        data = self.buf.getvalue()
        self.buf.truncate(0)
        self.buf.write(data[size:])
        return data[:size]
    
    def unread(self, data):
        self.buf.seek(0, os.SEEK_END)
        self.buf.write(data)
        
class ChunkedReader(object):
    def __init__(self, req, unreader):
        self.unreader = unreader
        self.req = req
        self.parser = self.parse_chunked(unreader)
        self.buf = StringIO()
    
    def read(self, size):
        if not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")
        if size <= 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return ""

        if self.parser:
            while self.buf.tell() < size:
                try:
                    self.buf.write(self.parser.next())
                except StopIteration:
                    self.parser = None
                    break

        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf.truncate(0)
        self.buf.write(rest)
        return ret
    
    def parse_trailers(self, unreader, data, eof=False):
        buf = StringIO()
        buf.write(data)
        
        idx = buf.getvalue().find("\r\n\r\n")
        done = buf.getvalue()[:2] == "\r\n"

        while idx < 0 and not done:
            self.get_data(unreader, buf)  
            idx = buf.getvalue().find("\r\n\r\n")
            done = buf.getvalue()[:2] == "\r\n"
        if done:
            unreader.unread(buf.getvalue()[2:])
            return ""
        self.req.trailers = self.req.parse_headers(buf.getvalue()[:idx])
        unreader.unread(buf.getvalue()[idx+4:])

    def parse_chunked(self, unreader):
        (size, rest) = self.parse_chunk_size(unreader)
        while size > 0:
            while size > len(rest):
                size -= len(rest)
                yield rest
                rest = unreader.read()
                if not rest:
                    raise NoMoreData()
            yield rest[:size]
            # Remove \r\n after chunk
            rest = rest[size:]
            while len(rest) < 2:
                rest += unreader.read()
            if rest[:2] != '\r\n':
                raise ChunkMissingTerminator(rest[:2])
            (size, rest) = self.parse_chunk_size(unreader, data=rest[2:])          

    def parse_chunk_size(self, unreader, data=None):
        buf = StringIO()
        if data is not None:
            buf.write(data)

        idx = buf.getvalue().find("\r\n")
        while idx < 0:
            self.get_data(unreader, buf)
            idx = buf.getvalue().find("\r\n")

        data = buf.getvalue()
        line, rest_chunk = data[:idx], data[idx+2:]
    
        chunk_size = line.split(";", 1)[0].strip()
        try:
            chunk_size = int(chunk_size, 16)
        except ValueError:
            raise InvalidChunkSize(chunk_size)

        if chunk_size == 0:
            try:
                self.parse_trailers(unreader, rest_chunk)
            except NoMoreData:
                pass
            return (0, None)
        return (chunk_size, rest_chunk)

    def get_data(self, unreader, buf):
        data = unreader.read()
        if not data:
            raise NoMoreData()
        buf.write(data)

class LengthReader(object):
    def __init__(self, req, unreader, length):
        self.req = req
        self.unreader = unreader
        self.length = length
    
    def read(self, size):
        if not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")
            
        size = min(self.length, size)
        if size < 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return ""       

        buf = StringIO()
        data = self.unreader.read()
        while data:
            buf.write(data)
            if buf.tell() >= size:
                break
            data = self.unreader.read()
        
        
        buf = buf.getvalue()
        ret, rest = buf[:size], buf[size:]
        self.unreader.unread(rest)
        self.length -= size
        return ret

class EOFReader(object):
    def __init__(self, req, unreader):
        self.req = req
        self.unreader = unreader
        self.buf = StringIO()
        self.finished = False
    
    def read(self, size):
        if not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")
        if size < 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return ""

        if self.finished:
            data = self.buf.getvalue()
            ret, rest = data[:size], data[size:]
            self.buf.truncate(0)
            self.buf.write(rest)
            return ret
         
        data = self.unreader.read()
        while data:
            self.buf.write(data)
            if self.buf.tell() > size:
                break
            data = self.unreader.read()

        if not data:
            self.finished = True
            
        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf.truncate(0)
        self.buf.write(rest)
        return ret

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
        data = self.read(8192)
        while data:
            data = self.read()

    def getsize(self, size):
        if size is None:
            return sys.maxint
        elif not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")
        elif size < 0:
            return sys.maxint
        return size
    
    def read(self, size=None):
        size = self.getsize(size)
        if size == 0:
            return ""

        if size < self.buf.tell():
            data = self.buf.getvalue()
            ret, rest = data[:size], data[size:]
            self.buf.truncate(0)
            self.buf.write(rest)
            return ret

        while size > self.buf.tell():
            data = self.reader.read(1024)
            if not len(data):
                self.closed = True
                break
            self.buf.write(data)

        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf.truncate(0)
        self.buf.write(rest)
        return ret
    
    def readline(self, size=None):
        size = self.getsize(size)
        if size == 0:
            return ""
        
        line = self.buf.getvalue()
        idx = line.find("\n")
        if idx >= 0:
            ret = line[:idx+1]
            self.buf.truncate(0)
            self.buf.write(line[idx+1:])
            return ret

        self.buf.truncate(0)
        ch = ""
        buf = [line]
        lsize = len(line)
        while lsize < size and ch != "\n":
            ch = self.reader.read(1)
            if not len(ch):
                self.closed = True
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
    def __init__(self, unreader, decompress=True):
        self.unreader = unreader
        self.version = None
        self.headers = MultiDict() 
        self.trailers = []
        self.body = None
        self.encoding = None
        self.status = None
        self.reason = None
        self.status_int = None
        self.decompress = decompress

        self.versre = re.compile("HTTP/(\d+).(\d+)")
        self.stare = re.compile("(\d{3})\s*(\w*)")
        self.hdrre = re.compile("[\x00-\x1F\x7F()<>@,;:\[\]={} \t\\\\\"]")

        unused = self.parse(self.unreader)
        self.unreader.unread(unused)
        self.set_body_reader()
        
    def get_data(self, unreader, buf, stop=False):
        data = unreader.read()
        if not data:
            if stop:
                raise StopIteration()
            raise NoMoreData(buf.getvalue())
        buf.write(data)
        
    def parse(self, unreader):
        buf = StringIO()

        self.get_data(unreader, buf, stop=True)
        
        # Request line
        idx = buf.getvalue().find("\r\n")
        while idx < 0:
            self.get_data(unreader, buf)
            idx = buf.getvalue().find("\r\n")
        self.parse_first_line(buf.getvalue()[:idx])
        rest = buf.getvalue()[idx+2:] # Skip \r\n
        buf.truncate(0)
        buf.write(rest)
        
        # Headers
        idx = buf.getvalue().find("\r\n\r\n")
        done = buf.getvalue()[:2] == "\r\n"
        while idx < 0 and not done:
            self.get_data(unreader, buf)
            idx = buf.getvalue().find("\r\n\r\n")
            done = buf.getvalue()[:2] == "\r\n"
        if done:
            self.unreader.unread(buf.getvalue()[2:])
            return ""

        self.headers = self.parse_headers(buf.getvalue()[:idx])

        ret = buf.getvalue()[idx+4:]
        buf.truncate(0)
        return ret
    
    def parse_first_line(self, line):
        bits = line.split(None, 1)
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

    def parse_headers(self, data):
        headers = MultiDict()

        # Split lines on \r\n keeping the \r\n on each line
        lines = [line + "\r\n" for line in data.split("\r\n")]

        # Parse headers into key/value pairs paying attention
        # to continuation lines.
        while len(lines):
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
            reader = ChunkedReader(self, self.unreader)
        elif clength is not None:
            reader = LengthReader(self, self.unreader, clength)
        else:
            reader = EOFReader(self, self.unreader)

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

