# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement
import os
import optparse as op
import sys

from restkit import __version__, request, set_logging

__usage__ = "'%prog [options] url [METHOD] [filename]'"

def options():
    """ build command lines options """
    return [
        op.make_option('-H', '--header', action='append', dest='headers',
                help='http string header in the form of Key:Value. '+
                'For example: "Accept: application/json" '),
        op.make_option('-S', '--server-response', action='store_true', 
                default=False, dest='server_response', 
                help='print server response'),
        op.make_option('--log-level', dest="log_level",
                help="Log level below which to silence messages. [info]",
                default="info"),
        op.make_option('-i', '--input', action='store', dest='input', 
                metavar='FILE', help='the name of the file to read from'),
        op.make_option('-o', '--output', action='store', dest='output',
                help='the name of the file to write to'),
        op.make_option('--follow-redirect', action='store_false', 
                dest='follow_redirect', default=True)
    ]

def main():
    """ function to manage restkit command line """
    parser = op.OptionParser(usage=__usage__, option_list=options(),
                    version="%prog " + __version__)
 
    opts, args = parser.parse_args()
    args_len = len(args)
    
    if args_len < 1:
        return parser.error('incorrect number of arguments')
        
    set_logging(opts.log_level)

    body = None
    headers = []
    if opts.input:
        if opts.input == '-':
            body = sys.stdin.read()
            headers.append(("Content-Length", str(len(body))))
        else:
            fname = os.path.normpath(os.path.join(os.getcwd(),opts.input))
            body = open(fname, 'r')
    
    if opts.headers:
        for header in opts.headers:
            try:
                k, v = header.split(':')
                headers.append((k, v))
            except ValueError:
                pass

    try:
        if args_len == 3:
            resp = request(args[0], method=args[1], body=body,
                        headers=headers, follow_redirect=opts.follow_redirect)
        elif len(args) == 2:
            if args[1] == "-":
                body = sys.stdin.read()
                headers.append(("Content-Length", str(len(body))))
        
            resp = request(args[0], method=args[1], body=body,
                        headers=headers, follow_redirect=opts.follow_redirect)
        else:
            if opts.input:
                method = 'POST'
            else:
                method='GET'
            resp = request(args[0], method=method, body=body,
                        headers=headers, follow_redirect=opts.follow_redirect)
                        
        if opts.output:
            with open(opts.output, 'wb') as f:
                if opts.log_level:
                    f.write("Server response from %s:\n" % resp.final_url)
                    for k, v in resp.headerslist:
                        f.write( "%s: %s" % (k, v))
                else:
                    for block in resp.body_file:
                        f.write(block)
        else:
            if opts.log_level:
                print "\n\033[0m\033[95mServer response from %s:\n\033[0m" % resp.final_url
                for k, v in resp.headerslist:
                    print "\033[94m%s\033[0m: %s" % (k, v)
                print "\033[0m"
            else:
                print resp.body
        
    except Exception, e:
        sys.stderr.write("An error happened: %s" % str(e))
        sys.stderr.flush()
        sys.exit(1)

    sys.exit(0)
    