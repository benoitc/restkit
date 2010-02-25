# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.



version_info = (0, 9, 5)
__version__ =  ".".join(map(str, version_info))

try:
    from restkit.errors import ResourceNotFound, Unauthorized, RequestFailed,\
RedirectLimit, RequestError, InvalidUrl, ResponseError, ProxyError, ResourceError
    from restkit.client import HttpConnection, HttpResponse
    from restkit.resource import Resource
    from restkit.pool import ConnectionPool
    
    # deprecated
    from restkit.rest import RestClient

except ImportError:
    import traceback
    traceback.print_exc()
    
    
def request(url, method='GET', body=None, headers=None, pool_instance=None):
    """ Quick shortcut method to pass a request """
    http_client = HttpConnection(pool_instance=pool_instance)
    return http_client.request(url, method=method, body=body, 
        headers=headers)