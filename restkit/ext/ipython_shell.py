# -*- coding: utf-8 -*-
import sys

try:
    from IPython.Shell import IPShellEmbed
except ImportError:
    raise ImportError('IPython (http://pypi.python.org/pypi/ipython) ' +\
                    'is required.')
                    
try:
    import webob
except ImportError:
    raise ImportError('webob (http://pythonpaste.org/webob/) is required.')

from restkit import __version__, request, set_logging
from restkit.console import common_indent, json
from restkit.ext.webob_api import Request as BaseRequest
from webob import Response as BaseResponse
from StringIO import StringIO
import IPython

class Stream(StringIO):
    def __repr__(self):
        return '<Stream(%s)>' % self.len


class JSON(Stream):
    def __init__(self, value):
        self.__value = value
        if json:
            Stream.__init__(self, json.dumps(value))
        else:
            Stream.__init__(self, value)
    def __repr__(self):
        return '<JSON(%s)>' % self.__value


class Response(BaseResponse):
    def __str__(self, skip_body=True):
        if self.content_length < 200 and skip_body:
            skip_body = False
        return BaseResponse.__str__(self, skip_body=skip_body)
    def __call__(self):
        print self


class Request(BaseRequest):
    ResponseClass = Response
    def get_response(self, *args, **kwargs):
        url = self.url
        stream = None
        for a in args:
            if isinstance(a, Stream):
                stream = a
                a.seek(0)
                continue
            elif isinstance(a, basestring):
                if a.startswith('http'):
                    url = a
                elif a.startswith('/'):
                    url = a

        self.set_url(url)

        if stream:
            self.body_file = stream
            self.content_length = stream.len
        if self.method == 'GET' and kwargs:
            for k, v in kwargs.items():
                self.GET[k] = v
        elif self.method == 'POST' and kwargs:
            for k, v in kwargs.items():
                self.GET[k] = v
        return BaseRequest.get_response(self)

    def __str__(self, skip_body=True):
        if self.content_length < 200 and skip_body:
            skip_body = False
        return BaseRequest.__str__(self, skip_body=skip_body)

    def __call__(self):
        print self


class ContentTypes(object):
    _values = {}
    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, sorted(self._values))
    def __str__(self):
        return '\n'.join(['%-20.20s: %s' % h for h in \
                                            sorted(self._value.items())])


ctypes = ContentTypes()
for k in common_indent:
    attr = k.replace('/', '_').replace('+', '_')
    ctypes._values[attr] = attr
    ctypes.__dict__[attr] = k
del k, attr


class API(property):
    def __get__(self, *args):
        return IPython.ipapi.get() or __IPYTHON__.api


class Shell(IPShellEmbed):
    def __init__(self, kwargs):
        argv = [
                 '-prompt_in1','\C_Blue\#) \C_Greenrestcli\$ ',
               ]
        IPShellEmbed.__init__(self,argv,banner='restkit shell %s' % __version__,
                              exit_msg=None,rc_override=None,
                              user_ns=kwargs)


class ShellClient(object):
    api = API()
    methods = dict(
            get='[req|url|path_info], **query_string',
            post='[req|url|path_info], [Stream()|**query_string_body]',
            head='[req|url|path_info], **query_string',
            put='[req|url|path_info], stream',
            delete='[req|url|path_info]')

    def __init__(self, url='/', options=None, **kwargs):
        self.options = options
        self.url = url or '/'
        self.ns = {}
        ipshell = Shell(self.ns)
        self.update_ns(self.ns)
        self.help()
        ipshell(header='', global_ns={}, local_ns={})

    def update_ns(self, ns):
        for k in self.methods:
            ns[k] = self.request_meth(k)
        stream = None
        headers = {}
        if self.options:
            if self.options.input:
                stream = Stream(open(self.options.input).read())
            if self.options.headers:
                for header in self.options.headers:
                    try:
                        k, v = header.split(':')
                        headers.append((k, v))
                    except ValueError:
                        pass
        req = Request.blank('/')
        req._client = self
        del req.content_type
        if stream:
            req.body_file = stream
        req.headers = headers
        req.set_url(self.url)
        ns.update(
                  Request=Request,
                  Response=Response,
                  Stream=Stream,
                  req=req,
                  stream=stream,
                  ctypes=ctypes,
                  )
        if json:
            ns['JSON'] = JSON

    def request_meth(self, k):
        def req(*args, **kwargs):
            resp = self.request(k.upper(), *args, **kwargs)
            self.api.to_user_ns(dict(resp=resp))
            print resp
            return resp
        req.func_name = k
        req.__name__ = k
        req.__doc__ =  """send a HTTP %s""" % k.upper()
        return req

    def request(self, meth, *args, **kwargs):
        """forward to restkit.request"""
        req = None
        for a in args:
            if isinstance(a, Request):
                req = a
                args = [a for a in args if a is not req]
                break
        if req is None:
            req = self.api.user_ns.get('req')
            if not isinstance(req, Request):
                req = Request.blank('/')
                del req.content_type
        req.method = meth
        req.set_url(self.url)
        resp = req.get_response(*args, **kwargs)
        self.url = req.url
        return resp

    def help(self):
        ns = self.ns.copy()
        methods = ''
        for k in sorted(self.methods):
            args = self.methods[k]
            doc = '  >>> %s(%s)' % (k, args)
            methods += '%-65.65s # send a HTTP %s\n' % (doc, k)
        ns['methods'] = methods
        print HELP.strip() % ns
        print ''

    def __repr__(self):
        return '<shellclient>'


def main(*args, **kwargs):
    for a in args:
        if a.startswith('http://'):
            kwargs['url'] = a
    ShellClient(**kwargs)


HELP = """
restkit shell
=============

HTTP Methods
------------

%(methods)s
Helpers
-------

  >>> req    # request to play with. By default http methods will use this one
  %(req)r

  >>> stream # Stream() instance if you specified a -i in command line
  %(stream)r

  >>> ctypes # Content-Types helper with headers properties
  %(ctypes)r
"""

if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
