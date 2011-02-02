
from gevent import monkey; monkey.patch_all()
import gevent

from restkit import *
from restkit.globals import set_manager
from restkit.manager.mgevent import GeventManager

#set_logging("debug")

urls = [
        "http://yahoo.fr",
        "http://google.com", 
        "http://friendpaste.com", 
        "http://benoitc.io", 
        "http://couchdb.apache.org"]

def fetch(u):
    c = Client()
    c.url = u
    c.follow_redirect=True
    r = c.perform()
    print "RESULT: %s: %s (%s)" % (u, r.status, len(r.body_string()))
    
allurls = []
for i in range(10):
    allurls.extend(urls)

jobs = [gevent.spawn(fetch, url) for url in allurls]
gevent.joinall(jobs)
