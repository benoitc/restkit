# -*- coding: utf-8 -
#
# Copyright (c) 2008 (c) Benoit Chesneau <benoitc@e-engura.com> 
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

import unittest

from restclient.utils import parse_url, iri2uri

class UtilTestCase(unittest.TestCase):
    
    def test_parse_url(self):
        """
        Validate that the parse_url() function properly returns the hostname, 
        port number, path (if any), and ssl boolean. Attempts several 
        different URL permutations, (5 tests total).
        """
        urls = {
            'http_noport_nopath': {
                'url':   'http://bogus.not',
                'host':  'bogus.not',
                'port':  80,
                'path':  '',
                'ssl':   False,
            },
            'https_noport_nopath': {
                'url':   'https://bogus.not',
                'host':  'bogus.not',
                'port':  443,
                'path':  '',
                'ssl':   True,
            },
            'http_noport_withpath': {
                'url':   'http://bogus.not/v1/bar',
                'host':  'bogus.not',
                'port':  80,
                'path':  'v1/bar',
                'ssl':   False,
            },
            'http_withport_nopath': {
                'url':   'http://bogus.not:8000',
                'host':  'bogus.not',
                'port':  8000,
                'path':  '',
                'ssl':   False,
            },
            'https_withport_withpath': {
                'url':   'https://bogus.not:8443/v1/foo',
                'host':  'bogus.not',
                'port':  8443,
                'path':  'v1/foo',
                'ssl':   True,
            },
        }
        for url in urls:
            yield check_url, url, urls[url]

    def check_url(test, urlspec):
        (host, port, path, ssl) = parse_url(urlspec['url'])
        self.assert_(host == urlspec['host'], "%s failed on host assertion" % test)
        self.assert_(port == urlspec['port'], "%s failed on port assertion" % test)
        self.assert_(path == urlspec['path'], "%s failed on path assertion" % test)
        self.assert_(ssl == urlspec['ssl'], "%s failed on ssl assertion" % test)
        
    def test_uris(self):
        """Test that URIs are invariant under the transformation."""
        invariant = [ 
            u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
            u"http://www.ietf.org/rfc/rfc2396.txt",
            u"ldap://[2001:db8::7]/c=GB?objectClass?one",
            u"mailto:John.Doe@example.com",
            u"news:comp.infosystems.www.servers.unix",
            u"tel:+1-816-555-1212",
            u"telnet://192.0.2.16:80/",
            u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
        for uri in invariant:
            self.assertEqual(uri, iri2uri(uri))
        
    def test_iri(self):
        """ Test that the right type of escaping is done for each part of the URI."""
        self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
        self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
        self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
        self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
        self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
        self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
        self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))
