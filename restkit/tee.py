# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.


"""
TeeInput replace old FileInput. It use a file
if size > MAX_BODY or memory. It's now possible to rewind
read or restart etc ... It's based on TeeInput from Gunicorn.

"""
import copy
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import tempfile

from restkit import conn

class TeeInput(object):

    CHUNK_SIZE = conn.CHUNK_SIZE

    def __init__(self, stream):
        self.buf = StringIO()
        self.eof = False

        if isinstance(stream, basestring):
            stream = StringIO(stream)
            self.tmp = StringIO()
        else:
            self.tmp = tempfile.TemporaryFile()

        self.stream = stream

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        return

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
        chunk = self.stream.read(length)
        if chunk:
            self.tmp.write(chunk)
            self.tmp.flush()
            self.tmp.seek(0, 2)
            return chunk

        self._finalize()
        return ""

    def _finalize(self):
        """ here we wil fetch final trailers
        if any."""
        self.eof = True

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

class ResponseTeeInput(TeeInput):

    CHUNK_SIZE = conn.CHUNK_SIZE

    def __init__(self, resp, connection, should_close=False):
        self.buf = StringIO()
        self.resp = resp
        self.stream =resp.body_stream()
        self.connection = connection
        self.should_close = should_close
        self.eof = False

        # set temporary body
        clen = int(resp.headers.get('content-length') or -1)
        if clen >= 0:
            if (clen <= conn.MAX_BODY):
                self.tmp = StringIO()
            else:
                self.tmp = tempfile.TemporaryFile()
        else:
            self.tmp = tempfile.TemporaryFile()

    def close(self):
        if not self.eof:
            # we didn't read until the end
            self._close_unreader()
        return self.tmp.close()

    def _close_unreader(self):
        if not self.eof:
            self.stream.close()
        self.connection.release(self.should_close)

    def _finalize(self):
        """ here we wil fetch final trailers
        if any."""
        self.eof = True
        self._close_unreader()
