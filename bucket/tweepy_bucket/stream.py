from tweepy import StreamListener
from tweepy.api import API
from models import *
import logging
import sys

class BucketListener(StreamListener):
    
    LOG_FILENAME = 'example_simple.log'
    logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)
    
    
    def __init__(self,api = None,bucket = None,ban_list_path = None):
        self.api = api or API()
        self.bucket = bucket or Bucket(bucket_size = 20)
        self.count = 0
        
       
        if ban_list_path is None:
            self.ban_list = BanList()
        else:
            self.ban_list = BanList(ban_list_path)
       
    def on_status(self,status):
        try:
            if self.count % 50 == 0:
                print 'Tweets: ',self.count
            self.count += 1
            
            if self.ban_list.check_ban(status.author.id):
                #print 'Filtered tweet from: %s' %status.author.screen_name
                return

            status.text.encode("utf-8")
            urls = self.extract_urls(status.text)
            urls = set(urls) #Eliminate duplicates
            
            for url in urls:
                simple_url = SimpleUrl(url,status.author)
                self.bucket.add_item(simple_url)
   
            if self.bucket.is_full:
                print '\n'
                print "BUCKET FULL"
                data = self.bucket.pour()
                self.post_data(data)
                print '\n'

                  
        except:
            # Catch any unicode errors while printing to console
            # and just ignore them to avoid breaking application.
            pass

    def extract_urls(self,text):
        import re
        url_list =re.findall("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",text)
        
        if len(url_list) == 0:
            return None
        
        return url_list
    
    
    def post_data(self,str):
        import urllib
        import urllib2
        
        #url = 'http://localhost:8000/task/'
        url = 'http://tweethitapp.appspot.com/task/'
        values = {'data' : str}

        print "posting to url: %s" %url
        data = urllib.urlencode(values)
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        #the_page = response.read()
        
        