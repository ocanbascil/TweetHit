import helipad
import logging

from google.appengine.ext import db
from google.appengine.api import taskqueue
from PerformanceEngine import LOCAL,MEMCACHE,DATASTORE,ALL_LEVELS,LIST,DICT,pdb

from tweethit.model import Url,Payload

from tweethit.utils.parser_util import ParserException,extract_urls
from tweethit.utils.rpc import UrlFetcher
from tweethit.utils.task_util import *
from config import *

import time
import datetime

from collections import defaultdict

class UrlBucketWorker(helipad.Handler):
  '''Deserialized incoming url dicts and checks if they've been fetched before
  if user of url mention is banned => do nothing
  if fetched => prepare counter payload
  not fetched => prepare fetch payload
  '''
  def post(self):
    payloads = [Payload(simple_url['url'],simple_url['user_id']) for simple_url in eval(self.request.get('data'))]
    
    cached_urls = Url.get_by_key_name([payload.url for payload in payloads],
                                      _storage = [LOCAL,MEMCACHE],
                                      _result_type = DICT)
    
    #user_ban_list = TwitterUser.get_banlist() #Ban filter
    user_ban_list = []
    
    fetch_targets = [] #Urls that are not in lookup list
    counter_targets = [] #Urls that were fetched before
    

    for payload in payloads:
      if payload.user_id in user_ban_list:
        #Don't take banned users' URLs into account
        continue
            
      #Look for existing cached instance with same short_url
      url_key =  str(db.Key.from_path('Url',payload.url))    
      cached_url = cached_urls[url_key]
      if cached_url is not None:
        if cached_url.is_product:
          counter_targets.append(Payload(cached_url.product_url,
                                                      payload.user_id, #We get user id from payload
                                                      cached_url.root_url,
                                                      cached_url.asin))
      else:
        fetch_targets.append(payload)                                 

    if len(fetch_targets):
      urlfetch_payload = Payload.serialize(fetch_targets)
      enqueue_url_fetch(urlfetch_payload)
    if len(counter_targets):
      counter_payload = Payload.serialize(counter_targets)
      enqueue_counter(counter_payload)
                                            
class UrlFetchWorker(helipad.Handler):
  '''Fetches all unprocessed URL headers to see if they 
  are directed to a Amazon Product Page
  
  Then creates mentions for all valid amazon products 
  and sends them to counter worker'''
  def post(self):
      
    fetch_targets = Payload.deserialize(self.request.get('payload'))
    #product_ban_list = Product.get_banlist()
    product_ban_list = []
    
    rpcs = []
    result_urls = []
    counter_targets = []
    
    for target in fetch_targets:
      fetcher = UrlFetcher()
      rpcs.append(fetcher.prepare_urlfetch_rpc(Url(key_name = target.url,user_id = target.user_id)))

    for item in rpcs:
      rpc = item[0]
      rpc.wait()
      url = item[1]
      result_urls.append(url)
                
    for url in result_urls:
      if not url.is_valid:
        continue #No action for invalid urls
      
      try:
        #These three may throw parser exceptions for invalid urls
        root_url = url.root_url
        product_url = url.product_url
        asin = url.asin
        user_id = url.user_id
        
        if product_url in product_ban_list:
            logging.info('Mention creation prevented for banned product url: %s' %product_url)
            continue #no action for banned product
        
        url.is_product = True #No exceptions for url.product_url or url.root_url => valid product reference
        
        counter_target = Payload(url.product_url,
                                            url.user_id,
                                            url.root_url,
                                            url.asin)
          
        counter_targets.append(counter_target)
      except ParserException,e:
        pass
                       
    pdb.put(result_urls, _storage = [LOCAL,MEMCACHE]) #Urls are stored in cache only
    
    counter_payload = Payload.serialize(counter_targets)
    
    timeout_ms = 100
    while True:      
      try:
        enqueue_counter(counter_payload)
        break      
      except taskqueue.TransientError:
        time.sleep(timeout_ms)
        timeout_ms *= 2
                

      
class CounterWorker(helipad.Handler):
  '''Updates counter entities for twitter_user and product models
  
  Input Payload: Serialized payload objects with product and user key names
  Output: Updates cached counter objects
  '''
  def post(self):
      payload_string = self.request.get('payload')
      counter_targets = Payload.deserialize(payload_string)

      '''
      flags = OperationFlags.retrieve()
      
      #Delay task if counters are being copied
      if not (flags.weekly_counter_copy and flags.monthly_counter_copy):
          enqueue_counter(payload_string,countdown = 60)
          return
      '''

      product_targets = defaultdict(int)
      user_targets = defaultdict(int)
      frequency = DAILY
      DAILY_SUFFIX = '|'+frequency
      
      for payload in counter_targets:
          product_targets[payload.url+DAILY_SUFFIX] += 1
          user_targets[payload.user_id+DAILY_SUFFIX] += 1
          
      product_dict = ProductCounter.new_get_multi(product_targets.keys())
      user_dict = UserCounter.new_get_multi(user_targets.keys())
      
      for key_name,delta in product_targets.iteritems():
          try:
              product_dict[key_name].count += delta
          except KeyError:
              product = Product(key_name = ProductCounter.build_parent_key_name(key_name))
              product_dict[key_name] = ProductCounter(key_name = key_name,
                                                                          count = delta,
                                                                          add_date = gmt_today(),
                                                                          frequency = frequency,
                                                                          store = product.store_key)
      for key_name,delta in user_targets.iteritems():  
          try:
              user_dict[key_name].count += delta
          except KeyError:
              user_dict[key_name] = UserCounter(key_name = key_name,count = delta,add_date = gmt_today())

      ProductCounter.filtered_update(product_dict.values())
      UserCounter.filtered_update(user_dict.values())

main, application = helipad.app({
    '/taskworker/bucket/': UrlBucketWorker,
    '/taskworker/url/': UrlFetchWorker,
})
'''
main, application = helipad.app({
    '/taskworker/cleanup/': CleanupWorker,
    '/taskworker/bucket/': UrlBucketWorker,
    '/taskworker/url/': UrlFetchWorker,
    '/taskworker/counter/': CounterWorker,
    '/taskworker/countercopy/': CounterCopier,
    '/taskworker/ban/product/':ProductBanWorker,
    '/taskworker/rendererinfo/':ProductRendererInfoFetcher,
    '/taskworker/rendererupdate/':ProductRendererUpdater,
})
'''

if __name__ == '__main__':
    main()
