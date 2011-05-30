# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement
import os
import optparse as op
import sys

# import pygments if here
try:
    import pygments
    from pygments.lexers import get_lexer_for_mimetype
    from pygments.formatters import TerminalFormatter
except ImportError:
    pygments = False
    
# import json   
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = False

from restkit import __version__, request, set_logging
from restkit.util import popen3, locate_program

__usage__ = "'%prog [options] url [METHOD] [filename]'"


pretties = {
    'application/json': 'text/javascript',
    'text/plain': 'text/javascript'
}

def external(cmd, data):
    try:
        (child_stdin, child_stdout, child_stderr) = popen3(cmd)
        err = child_stderr.read()
        if err:
            return data
        return child_stdout.read()
    except:
        return data
        
def indent_xml(data):
    tidy_cmd = locate_program("tidy")
    if tidy_cmd:
        cmd = " ".join([tidy_cmd, '-qi', '-wrap', '70', '-utf8', data])
        return external(cmd, data)
    return data
    
def indent_json(data):
    if not json:
        return data
    info = json.loads(data)
    return json.dumps(info, indent=2, sort_keys=True)


common_indent = {
    'application/json': indent_json,
    'text/html': indent_xml,
    'text/xml': indent_xml,
    'application/xhtml+xml': indent_xml,
    'application/xml': indent_xml,
    'image/svg+xml': indent_xml,
    'application/rss+xml': indent_xml,
    'application/atom+xml': indent_xml,
    'application/xsl+xml': indent_xml,
    'application/xslt+xml': indent_xml
}

def indent(mimetype, data):
    if mimetype in common_indent:
        return common_indent[mimetype](data)
    return data
    
def prettify(response, cli=True):
    if not pygments or not 'content-type' in response.headers:
        return response.body_string()
        
    ctype = response.headers['content-type']
    try:
        mimetype, encoding = ctype.split(";")
    except ValueError:
        mimetype = ctype.split(";")[0]
        
    # indent body
    body = indent(mimetype, response.body_string())
    
    # get pygments mimetype
    mimetype = pretties.get(mimetype, mimetype)
    
    try:
        lexer = get_lexer_for_mimetype(mimetype)
        body = pygments.highlight(body, lexer, TerminalFormatter())
        return body
    except:
        return body

def as_bool(value):
    if value.lower() in ('true', '1'):
        return True
    return False

def update_defaults(defaults):
    config = os.path.expanduser('~/.restcli')
    if os.path.isfile(config):
        for line in open(config):
            key, value = line.split('=', 1)
            key = key.lower().strip()
            key = key.replace('-', '_')
            if key.startswith('header'):
                key = 'headers'
            value = value.strip()
            if key in defaults:
                default = defaults[key]
                if default in (True, False):
                    value = as_bool(value)
                elif isinstance(default, list):
                    default.append(value)
                    value = default
                defaults[key] = value

def options():
    """ build command lines options """

    defaults = dict(
            headers=[],
            request='GET',
            follow_redirect=False,
            server_response=False,
            prettify=False,
            log_level=None,
            input=None,
            output=None,
            )
    update_defaults(defaults)

    def opt_args(option, *help):
        help = ' '.join(help)
        help = help.strip()
        default = defaults.get(option)
        if default is not None:
            help += ' Default to %r.' % default
        return dict(default=defaults.get(option), help=help)

    return [
        op.make_option('-H', '--header', action='append', dest='headers',
                **opt_args('headers',
                           'HTTP string header in the form of Key:Value. ',
                           'For example: "Accept: application/json".')),
        op.make_option('-X', '--request', action='store', dest='method',
                       **opt_args('request', 'HTTP request method.')),
        op.make_option('--follow-redirect', action='store_true',
                       dest='follow_redirect', **opt_args('follow_redirect')),
        op.make_option('-S', '--server-response', action='store_true',
                       dest='server_response',
                       **opt_args('server_response', 'Print server response.')),
        op.make_option('-p', '--prettify', dest="prettify", action='store_true',
                       **opt_args('prettify', "Prettify display.")),
        op.make_option('--log-level', dest="log_level",
                       **opt_args('log_level',
                                  "Log level below which to silence messages.")),
        op.make_option('-i', '--input', action='store', dest='input',
                       metavar='FILE',
                       **opt_args('input', 'The name of the file to read from.')),
        op.make_option('-o', '--output', action='store', dest='output',
                       **opt_args('output', 'The name of the file to write to.')),
        op.make_option('--shell', action='store_true', dest='shell',
                       help='Open a IPython shell'),
    ]

def main():
    """ function to manage restkit command line """
    parser = op.OptionParser(usage=__usage__, option_list=options(),
                    version="%prog " + __version__)

    opts, args = parser.parse_args()
    args_len = len(args)

    if opts.shell:
        try:
            from restkit.contrib import ipython_shell as shell
            shell.main(options=opts, *args)
        except Exception, e:
            print >>sys.stderr, str(e)
            sys.exit(1)
        return

    if args_len < 1:
        return parser.error('incorrect number of arguments')

    if opts.log_level is not None:
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
        if len(args) == 2:
            if args[1] == "-" and not opts.input:
                body = sys.stdin.read()
                headers.append(("Content-Length", str(len(body))))

        if not opts.method and opts.input:
            method = 'POST'
        else:
            method=opts.method.upper()
            
        resp = request(args[0], method=method, body=body,
                    headers=headers, follow_redirect=opts.follow_redirect)
                        
        if opts.output and opts.output != '-':
            with open(opts.output, 'wb') as f:
                if opts.server_response:
                    f.write("Server response from %s:\n" % resp.final_url)
                    for k, v in resp.headerslist:
                        f.write( "%s: %s" % (k, v))
                else:
                    with resp.body_stream() as body:
                        for block in body:
                            f.write(block)
        else:
            if opts.server_response:
                if opts.prettify:
                    print "\n\033[0m\033[95mServer response from %s:\n\033[0m" % (
                                                                    resp.final_url)
                    for k, v in resp.headerslist:
                        print "\033[94m%s\033[0m: %s" % (k, v)
                    print "\033[0m"
                else:
                    print "Server response from %s:\n" % (resp.final_url)
                    for k, v in resp.headerslist:
                        print "%s: %s" % (k, v)
                    print ""

                if opts.output == '-':
                    if opts.prettify:
                        print prettify(resp)
                    else:
                        print resp.body_string()
            else:
                if opts.prettify:
                    print prettify(resp)
                else:
                    print resp.body_string()
        
    except Exception, e:
        sys.stderr.write("An error happened: %s" % str(e))
        sys.stderr.flush()
        sys.exit(1)

    sys.exit(0)
    
