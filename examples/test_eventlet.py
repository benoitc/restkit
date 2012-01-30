import timeit

import eventlet
eventlet.monkey_patch()

from restkit import *
from restkit.conn import Connection
from socketpool import ConnectionPool

#set_logging("debug")

pool = ConnectionPool(factory=Connection, backend="eventlet")

epool = eventlet.GreenPool()

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
    for url in allurls:
        epool.spawn_n(fetch, url)
    epool.waitall()

t = timeit.Timer(stmt=extract)
print "%.2f s" % t.timeit(number=1)
