import threading
from restkit import *

set_logging("debug")

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
    

for i in range(10):
    
    for u in urls:
        t =  threading.Thread(target=fetch, args=[u])
        t.daemon = True
        t.start()

t.join()
