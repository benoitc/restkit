# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


"""
TeeInput replace old FileInput. It use a file 
if size > MAX_BODY or memory. It's now possible to rewind
read or restart etc ... It's based on TeeInput from Gunicorn.

"""
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import tempfile


from restkit.http.body import ChunkedReader, LengthReader, EOFReader
from restkit.errors import UnexpectedEOF
from restkit.util import sock

class TeeInput(object):
    
    CHUNK_SIZE = sock.CHUNK_SIZE
    
    def __init__(self, response, release_connection = None):
        self.buf = StringIO()
        self.response = response
        self.release_connection = release_connection
        self._len = None
        self._clen = 0
        self.eof = False
        
        # set temporary body
        if isinstance(response.body.reader, LengthReader):
            self._len = response.body.reader.length 
            if (response.body.reader.length <= sock.MAX_BODY):
                self.tmp = StringIO()
            else:
                self.tmp = tempfile.TemporaryFile()
        else:
            self.tmp = tempfile.TemporaryFile()
                       
    @property
    def len(self):
        if self._len is not None: 
            return self._len
        
        if not self.eof:
            pos = self.tmp.tell()
            self.tmp.seek(0, 2)
            while True:
                if not self._tee(self.CHUNK_SIZE):
                    break
            self.tmp.seek(pos)
        self._len = self._tmp_size()
        return self._len
    __len__ = len
        
    def seek(self, offset, whence=0):
        """ naive implementation of seek """
        current_size = self._tmp_size()
        diff = 0
        if whence == 0:
            diff = offset - current_size                     
        elif whence == 2:
            diff = (self.tmp.tell() + offset) - current_size     
        elif whence == 3 and not self.eof:
            # we read until the end
            while True:
                self.tmp.seek(0, 2)
                if not self._tee(self.CHUNK_SIZE):
                    break
                    
        if not self.eof and diff > 0:
            self._ensure_length(StringIO(), diff)
        self.tmp.seek(offset, whence)

    def flush(self):
        self.tmp.flush()
        
    def read(self, length=-1):
        """ read """
        if self.eof:
            return self.tmp.read(length)
            
        if length < 0:
            buf = StringIO()
            buf.write(self.tmp.read())
            while True:
                chunk = self._tee(self.CHUNK_SIZE)
                if not chunk: 
                    break
                buf.write(chunk)
            return buf.getvalue()
        else:
            dest = StringIO()
            diff = self._tmp_size() - self.tmp.tell()
            if not diff:
                dest.write(self._tee(length))
                return self._ensure_length(dest, length)
            else:
                l = min(diff, length)
                dest.write(self.tmp.read(l))
                return self._ensure_length(dest, length)
                
    def readline(self, size=-1):
        if self.eof:
            return self.tmp.readline()
        
        orig_size = self._tmp_size()
        if self.tmp.tell() == orig_size:
            if not self._tee(self.CHUNK_SIZE):
                return ''
            self.tmp.seek(orig_size)
        
        # now we can get line
        line = self.tmp.readline()
        if line.find("\n") >=0:
            return line

        buf = StringIO()
        buf.write(line)
        while True:
            orig_size = self.tmp.tell()
            data = self._tee(self.CHUNK_SIZE)
            if not data:
                break
            self.tmp.seek(orig_size)
            buf.write(self.tmp.readline())
            if data.find("\n") >= 0:
                break
        return buf.getvalue()
       
    def readlines(self, sizehint=0):
        total = 0
        lines = []
        line = self.readline()
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline()
        return lines
    
    def close(self):
        if not self.eof:
            # we didn't read until the end
            self._close_unreader()
        return self.tmp.close()
    
    def next(self):
        r = self.readline()
        if not r:
            raise StopIteration
        return r
    __next__ = next
    
    def __iter__(self):
        return self    

    def _tee(self, length):
        """ fetch partial body"""
        buf2 = self.buf
        buf2.seek(0, 2) 
        chunk = self.response.body.read(length)
        if chunk:
            self.tmp.write(chunk)
            self.tmp.flush()
            self.tmp.seek(0, 2)
            self._clen += len(chunk)
            
            # do we need to close the socket
            if self._len is not None and self._clen >= self._len:
                self._finalize()
            return chunk
                
        self._finalize()
        return ""
        
    def _close_unreader(self):
        if self.response.should_close():
            self.response.unreader.close()
        elif callable(self.release_connection):
            if not self.eof:
                # read remaining data
                while True:
                    if not self.response.body.read(self.CHUNK_SIZE):
                        break          
            self.release_connection()
            
    def _finalize(self):
        """ here we wil fetch final trailers
        if any."""
        self.eof = True
        self._close_unreader()

    def _tmp_size(self):
        if hasattr(self.tmp, 'fileno'):
            return int(os.fstat(self.tmp.fileno())[6])
        else:
            return len(self.tmp.getvalue())
            
    def _ensure_length(self, dest, length):
        if len(dest.getvalue()) < length:
            data = self._tee(length - len(dest.getvalue()))
            dest.write(data)
        return dest.getvalue()
