import timeit

import eventlet 
eventlet.monkey_patch()

from restkit import *
from restkit.globals import set_manager, get_manager
from restkit.manager.meventlet import EventletManager

#set_logging("debug")

print "Manager was: %s" % type(get_manager())
set_manager(EventletManager())
print"Manager is set to: %s" %type(get_manager())

pool = eventlet.GreenPool()

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
    r = request(u, follow_redirect=True)
    print "RESULT: %s: %s (%s)" % (u, r.status, len(r.body_string()))

def extract():
    for url in allurls:
        pool.spawn_n(fetch, url)
    pool.waitall()

t = timeit.Timer(stmt=extract)
print "%.2f s" % t.timeit(number=1)
