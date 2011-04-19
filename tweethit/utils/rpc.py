# -*- coding: utf-8 -*-
from google.appengine.api import urlfetch
from google.appengine.api import apiproxy_stub_map
from google.appengine.api.urlfetch import DownloadError
from google.appengine.ext.db import BadValueError

import amazonproduct
import time
from config import DEBUG_MODE

# DeadlineExceededError can live in two different places 
try: 
  from google.appengine.runtime import DeadlineExceededError #Deploy
except ImportError: 
  from google.appengine.runtime.apiproxy_errors import DeadlineExceededError #Debug

import logging
from secret import *
from amazonproduct import API, AWSError

if DEBUG_MODE:
    DEFAULT_THUMB_URL = "http://localhost:8000/images/default_thumb.gif"
else:
    DEFAULT_THUMB_URL = "http://tweethitapp.appspot.com/images/default_thumb.gif"
 
class AmazonProductFetcher(object):
  """
  Fetch product information using Amazon Product API
  Save the results into a ProductDetail instance
  3 Fetches are Made:
  1- Product details = title, product_group
  2- Prices details = lowest price of new items
  3- Image details = urls for small, medium, large images
  
  This service will be called by product renderer taskworker
  """
  @classmethod
  def get_product_details(cls,asin,product_renderer,locale = 'us'):
    
    logging.info('AmazonProductFetcher.get_product_details called, asin: %s, locale: %s' %(asin,locale))
    api = API(AWS_KEY, SECRET_KEY, locale)
    timeout_ms = 100
    while True:
      try:
        product_node = api.item_lookup(id=asin)  #title,product group
        image_node = api.item_lookup(id=asin, ResponseGroup='Images') #Images
        break
      except amazonproduct.TooManyRequests:
        time.sleep(timeout_ms)
        timeout_ms *= 2                            
      except AWSError:
        logging.error('Could not retrieve info for product %s' % asin)
        return
      except DownloadError,e:
        logging.error('%s retrieving URLfor product: %s in RPC'   %(e,asin))
        return #Early quit
    
    #Extract values from BeautifulSoup nodes
    try:
      title = product_node.find('title').string.encode('utf-8')[:500] #StringProperty upper limit
    except AttributeError,e: #This means invalid url parsing, no valid ASIN value
      logging.error('%s setting title in RPC'   %e)
      return #Early quit
        
    product_group = product_node.find('productgroup').string.encode('utf-8')

    try:
      image_small =  str(image_node.find('smallimage').find('url').string)
      image_medium=  str(image_node.find('mediumimage').find('url').string)
      image_large=  str(image_node.find('largeimage').find('url').string)
    except AttributeError:
      image_small =  DEFAULT_THUMB_URL
      image_medium=  None
      image_large=  None
        
    product_renderer.title =  unicode(title,'utf-8') #For urls with funky characters
    product_renderer.product_group = unicode(product_group,'utf-8')
    product_renderer.image_small = image_small
    product_renderer.image_medium = image_medium
    product_renderer.image_large = image_large
    
    return product_renderer    
  
class UrlFetcher(object):
  
  @classmethod
  def fetch_urls(cls,url_list):
    rpcs = []
    for url in url_list:
      rpc = urlfetch.create_rpc(deadline=5.0)
      urlfetch.make_fetch_call(rpc, url,method = urlfetch.HEAD)
      rpcs.append(rpc)
      
    result = {}
    while len(rpcs) > 0:
      rpc = apiproxy_stub_map.UserRPC.wait_any(rpcs)
      rpcs.remove(rpc)
      request_url = rpc.request.url()
      try:
        final_url = rpc.get_result().final_url
      except AttributeError:
        final_url = request_url
      except DownloadError:
        final_url  = None
      except UnicodeDecodeError: #Funky url with very evil characters
        final_url = unicode(rpc.get_result().final_url,'utf-8')
        
      result[request_url] = final_url
    
    return result

    
         
class UrlFetcher2(object):
  def prepare_urlfetch_rpc(self,url_model):
    self.rpc = urlfetch.create_rpc(callback=self.process_result,deadline=5.0)
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