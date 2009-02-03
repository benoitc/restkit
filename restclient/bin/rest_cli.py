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
import os
import sys
from optparse import OptionParser, OptionGroup
import urlparse
import urllib

# python 2.6 and above compatibility
try:
    from urlparse import parse_qs as _parse_qs
except ImportError:
    from cgi import parse_qs as _parse_qs

import restclient
from restclient.transport import useCurl, CurlTransport, HTTPLib2Transport

class Url(object):
    def __init__(self, string):
        parts = urlparse.urlsplit(urllib.unquote(string))
        if parts[0] != 'http' and parts[0] != 'https':
            raise ValueError('Invalid url: %s.' % string)

        if "@" in parts[1]:
            host = parts[1].split('@').pop()
        else:
            host = parts[1]
       
        self.hostname = host
        if parts[0] == 'http':
            self.port = 80
        else:
            self.port = 443

        if ":" in host:
            try:
                self.hostname, self.port = host.split(':')
            except:
                raise ValueError('Invalid url: %s.' % string)

            self.port = int(self.port)

        self.uri = "%s://%s" % (parts[0], host)

        if parts[2]:
            self.path = parts[2]
        else:
            self.path = ''

        if parts[3]:
            self.query = _parse_qs(parts[3])
        else:
            self.query = {}

        self.username = parts.username
        self.password = parts.password


def make_query(string, method='GET', fname=None, 
        list_headers=None, output=None, proxy=None):
    try:
        uri = Url(string)
    except ValueError, e:
        print >>sys.stderr, e
        return 

    transport = None 
    proxy_infos = None
    if proxy and proxy is not None:
        try:
            proxy_url = Url(proxy)
        except:
            print >>sys.stderr, "proxy url is invalid"
            return
        proxy_infos = { "proxy_host": proxy_url.hostname }
        if proxy_url.port is not None:
            proxy_infos["proxy_port"] = proxy_url.port
        if proxy_url.username and proxy_url.username is not None:
            proxy_infos["proxy_username"] = proxy_url.username
            proxy_infos["proxy_password"] = proxy_url.password or ''

    if useCurl():
        transport = CurlTransport(proxy_infos=proxy_infos)
    else:
        transport = HTTPLib2Transport(proxy_infos=proxy_infos)
    
    if uri.username:
        transport.add_credentials(uri.username, uri.password) 
    
    res = restclient.Resource(uri.uri, transport=transport)

    list_headers = list_headers or []
    headers = {}
    if list_headers:
        for header in list_headers:
            if ":" in header:
                k, v = header.split(':')
                headers[k] = v

    payload = None
    if fname:
        if fname == '-':
            payload = sys.stdin.read()
            headers['Content-Length'] = len(payload)
        else:
            fname = os.path.normpath(os.path.join(os.getcwd(),fname))
            headers['Content-Length'] = os.path.getsize(fname)
            payload = open(fname, 'r')

    data = res.request(method, path=uri.path, payload=payload, headers=headers, **uri.query)

    output = output or ''
    if not output or output == '-':
        return data
    else:
        try:
            f = open(output, 'wb')
            f.write(data)
            f.close()
        except:
            print >>sys.stderr, "Can't save result in %s" % output
            return


def main():
    parser = OptionParser(usage='%prog [options] url [METHOD] [filename]', version="%prog " + restclient.__version__)
    parser.add_option('-H', '--header', action='append', dest='headers',
            help='http string header in the form of Key:Value. '+
            'For example: "Accept: application/json" ')
    parser.add_option('-i', '--input', action='store', dest='input', metavar='FILE',
                      help='the name of the file to read from')
    parser.add_option('-o', '--output', action='store', dest='output',
                      help='the name of the file to read from')

    parser.add_option('--proxy', action='store', dest='proxy',
            help='Full uri of proxy, ex:\n'+
            'http://username:password@proxy:port/')

    options, args = parser.parse_args()

    if len(args) < 1:
        return parser.error('incorrect number of arguments')
    if options.input:
        fname=options.input
    else:
        fname=None
   
    if len(args) == 3:
        return make_query(args[0], method=args[1], fname=args[2], 
                list_headers=options.headers, output=options.output,
                proxy=options.proxy)
    
    elif len(args) == 2:
        if args[1] == "-":
            return make_query(args[0], method='POST', fname=args[1], 
                    list_headers=options.headers, output=options.output,
                    proxy=options.proxy)
        return make_query(args[0], method=args[1], fname=fname, 
                list_headers=options.headers, output=options.output,
                proxy=options.proxy)
    else:
        if options.input:
            method = 'POST'
        else:
            method='GET'
        return make_query(args[0], method=method, fname=fname, 
                list_headers=options.headers, output=options.output,
                proxy=options.proxy)


if __name__ == '__main__':
    main()
