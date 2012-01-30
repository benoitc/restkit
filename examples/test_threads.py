import threading
import timeit
from restkit import *

#set_logging("debug")

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

def spawn(u):
    t =  threading.Thread(target=fetch, args=[u])
    t.daemon = True
    t.start()
    return t

def extract():
    threads = [spawn(u) for u in allurls]
    [t.join() for t in threads]

t = timeit.Timer(stmt=extract)
print "%.2f s" % t.timeit(number=1)
