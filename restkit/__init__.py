# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


try:
    __version__ = __import__('pkg_resources').get_distribution('restkit').version
except:
    __version__ = '?'

USER_AGENT = "restkit/%s" % __version__

debuglevel = 0

from restkit.errors import *
from restkit.client import HttpConnection, HttpResponse
from restkit.rest import Resource, RestClient



