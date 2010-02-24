# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

__version__ = "0.9.5"

USER_AGENT = "restkit/%s" % __version__

debuglevel = 0

from restkit.errors import *
from restkit.client import HttpConnection, HttpResponse
from restkit.resource import Resource
from restkit.rest import RestClient



