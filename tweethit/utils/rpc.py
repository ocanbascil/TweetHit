# -*- coding: utf-8 -*-
from google.appengine.api import urlfetch
from google.appengine.api.urlfetch import DownloadError
from google.appengine.ext.db import BadValueError

import amazonproduct
import time

# DeadlineExceededError can live in two different places 
try: 
  from google.appengine.runtime import DeadlineExceededError #Deploy
except ImportError: 
  from google.appengine.runtime.apiproxy_errors import DeadlineExceededError #Debug

import logging
from secret import *
from BeautifulSoup import BeautifulSoup
from amazonproduct import API, ResultPaginator, AWSError

if DEBUG_MODE:
    DEFAULT_THUMB_URL = "http://localhost:8000/images/default_thumb.gif"
else:
    DEFAULT_THUMB_URL = "http://tweethitapp.appspot.com/images/default_thumb.gif"
    
class UrlFetcher(object):
  def prepare_urlfetch_rpc(self,url_model):
    self.rpc = urlfetch.create_rpc(callback=self.process_result)
    self.url_model = url_model
    urlfetch.make_fetch_call(self.rpc, self.url_model.key().name(),method = urlfetch.HEAD)
    return self.rpc,self.url_model
        
  def process_result(self):
    #logging.info('Original url in UrlFetcher process_result(): %s' %self.url_model.key().name())
    try:
      result = self.rpc.get_result()
      
      if result.final_url is None: #There's no final url, short_url is what we need
        self.set_valid_url(self.url_model.key().name())
      else:
        try:
          #logging.info('Final url in UrlFetcher process_result(): %s' %result.final_url)
          self.set_valid_url(result.final_url)
        except BadValueError,e: #This happens when somehow half final_url is returned like "/forums/something/something/"
          logging.warning('%s while saving url: %s' % (e,self.url_model.key().name()))
        except UnicodeDecodeError, e: #Funky url with very evil characters
          url = unicode(result.final_url,'utf-8')
          self.set_valid_url(url)
                                    
    except urlfetch.Error, e:# Handle urlfetch errors...
      logging.warning('%s while retrieving url: %s' % (e,self.url_model.key().name()))
    except UnicodeError,e: # Label too long or empty...       
      logging.warning('%s while retrieving url: %s' % (e,self.url_model.key().name()))
    except DeadlineExceededError,e: #Took too long to fetch the url    
      logging.warning('%s while retrieving url: %s' % (e,self.url_model.key().name()))

  def set_valid_url(self,final_url):
    self.url_model.final_url = final_url
    self.url_model.is_valid = True