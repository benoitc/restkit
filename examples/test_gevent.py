import timeit

from gevent import monkey; monkey.patch_all()
import gevent

from restkit import *
from restkit.conn import Connection
from socketpool import ConnectionPool

#set_logging("debug")

pool = ConnectionPool(factory=Connection, backend="gevent")

urls = [
        "http://yahoo.fr",
        "http://google.com",
        "http://friendpaste.com",
        "http://benoitc.io",
        "http://couchdb.apache.org"]

allurls = []
for i in range(10):
    allurls.extend(urls)

def fetch(u):
    r = request(u, follow_redirect=True, pool=pool)
    print "RESULT: %s: %s (%s)" % (u, r.status, len(r.body_string()))

def extract():

    jobs = [gevent.spawn(fetch, url) for url in allurls]
    gevent.joinall(jobs)

t = timeit.Timer(stmt=extract)
print "%.2f s" % t.timeit(number=1)
