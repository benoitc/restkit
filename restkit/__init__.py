# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.



version_info = (3, 0, 1)
__version__ =  ".".join(map(str, version_info))

try:
    from .errors import ResourceNotFound, Unauthorized, RequestFailed,\
RedirectLimit, RequestError, InvalidUrl, ResponseError, ProxyError, ResourceError
    from .client import Client, ClientResponse, MAX_FOLLOW_REDIRECTS
    from .resource import Resource
    from .manager import Manager 
    from .filters import BasicAuth, SimpleProxy, OAuthFilter
except ImportError:
    import traceback
    traceback.print_exc()

import urlparse
import logging    

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG
}

def set_logging(level, handler=None):
    """
    Set level of logging, and choose where to display/save logs 
    (file or standard output).
    """
    if not handler:
        handler = logging.StreamHandler()

    loglevel = LOG_LEVELS.get(level, logging.INFO)
    logger = logging.getLogger('restkit')
    logger.setLevel(loglevel)
    format = r"%(asctime)s [%(process)d] [%(levelname)s] %(message)s"
    datefmt = r"%Y-%m-%d %H:%M:%S"
    
    handler.setFormatter(logging.Formatter(format, datefmt))
    logger.addHandler(handler)
    
    
def request(url, 
        method='GET', 
        body=None, 
        headers=None,  
        **kwargs):
    """ Quick shortcut method to pass a request
    
    :param url: str, url string
    :param method: str, by default GET. http verbs
    :param body: the body, could be a string, an iterator or a file-like object
    :param headers: dict or list of tupple, http headers
    :pool intance: instance inherited from `restkit.pool.PoolInterface`. 
    It allows you to share and reuse connections connections.
    :param follow_redirect: boolean, by default is false. If true, 
    if the HTTP status is 301, 302 or 303 the client will follow
    the location.
    :param filters: list, list of http filters. see the doc of http filters 
    for more info
    :param ssl_args: ssl arguments. See http://docs.python.org/library/ssl.html
    for more information.
    
    """
    # detect credentials from url
    u = urlparse.urlparse(url)
    if u.username is not None:
        password = u.password or ""
        filters = kwargs.get('filters') or []
        url = urlparse.urlunparse((u.scheme, u.netloc.split("@")[-1],
            u.path, u.params, u.query, u.fragment))
        filters.append(BasicAuth(u.username, password))
  
        kwargs['filters'] = filters
    
    http_client = Client(**kwargs)
    return http_client.request(url, method=method, body=body, 
            headers=headers)
