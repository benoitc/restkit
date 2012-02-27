# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

from restkit.version import version_info, __version__

try:
    from restkit.conn import Connection
    from restkit.errors import ResourceNotFound, Unauthorized, RequestFailed,\
RedirectLimit, RequestError, InvalidUrl, ResponseError, ProxyError, \
ResourceError, ResourceGone
    from restkit.client import Client, MAX_FOLLOW_REDIRECTS
    from restkit.wrappers import Request, Response, ClientResponse
    from restkit.resource import Resource
    from restkit.filters import BasicAuth, OAuthFilter
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

    Client parameters
    ~~~~~~~~~~~~~~~~~

    :param follow_redirect: follow redirection, by default False
    :param max_ollow_redirect: number of redirections available
    :filters: http filters to pass
    :param decompress: allows the client to decompress the response
    body
    :param max_status_line_garbage: defines the maximum number of ignorable
    lines before we expect a HTTP response's status line. With
    HTTP/1.1 persistent connections, the problem arises that broken
    scripts could return a wrong Content-Length (there are more
    bytes sent than specified).  Unfortunately, in some cases, this
    cannot be detected after the bad response, but only before the
    next one. So the client is abble to skip bad lines using this
    limit. 0 disable garbage collection, None means unlimited number
    of tries.
    :param max_header_count:  determines the maximum HTTP header count
    allowed. by default no limit.
    :param manager: the manager to use. By default we use the global
    one.
    :parama response_class: the response class to use
    :param timeout: the default timeout of the connection
    (SO_TIMEOUT)

    :param max_tries: the number of tries before we give up a
    connection
    :param wait_tries: number of time we wait between each tries.
    :param ssl_args: ssl named arguments,
    See http://docs.python.org/library/ssl.html informations
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
