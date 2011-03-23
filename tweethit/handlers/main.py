import helipad
from google.appengine.ext import db
from google.appengine.api import taskqueue

import config
import secret
import logging

import datetime
import time
from collections import defaultdict

helipad.root('tweethit').template_root('static/templates/')

root_url = 'http://localhost:8000'
#root_url = 'http://www.tweethit.com'

    
class ProjectsHandler(helipad.Handler):
    def get(self, id):
        self.response.out.write("This is project #%s" % id)
        
class NotFoundHandler(helipad.Handler):
    def get(self):
        self.response.out.write("Page not found")
  
class BucketHandler(helipad.Handler):
    def get(self):
        logging.info('Bucket get called')
        self.response.out.write('Bucket get called')

    def post(self):
        data = self.request.get('data')
        logging.info('Bucket Handler called')
        #Add the task to the default queue.
        timeout_ms = 100
        while True:      
            try:
                taskqueue.add(url='/taskworker/bucket/', params={'data': data})
                break      
            except taskqueue.TransientError:
                time.sleep(timeout_ms)
                timeout_ms *= 2

class AffiliateRedirectHandler(helipad.Handler):
    pass
        
main, application = helipad.app([
    ('/task/', BucketHandler),
    ('/.*',NotFoundHandler),

])

if __name__ == '__main__':
  main()
