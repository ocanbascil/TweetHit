import helipad
import logging

from google.appengine.ext import db
from google.appengine.api import taskqueue
from PerformanceEngine import LOCAL,MEMCACHE,DATASTORE,ALL_LEVELS,LIST,DICT,pdb

from tweethit.model import *

from tweethit.utils.parser_util import ParserException,extract_urls
from tweethit.utils.rpc import UrlFetcher
from tweethit.utils.task_util import *
from tweethit.utils.time_util import gmt_today
from config import *

import time

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
    counter_targets = [] #Product urls that were fetched before
    
    for payload in payloads:
      if payload.user_id in user_ban_list:
        #Don't take banned users' URLs into account
        continue
            
      #Look for existing cached instance with same short_url
      url_key =  str(db.Key.from_path('Url',payload.url))    
      cached_url = cached_urls[url_key]
      if cached_url is not None:
        if cached_url.is_product: #cached url points to a valid product page
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
    
    if len(counter_targets):
      counter_payload = Payload.serialize(counter_targets)
    else:
      return #Early exit if no counters targets are found
    
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
    from collections import defaultdict
    payload_string = self.request.get('payload')
    counter_targets = Payload.deserialize(payload_string)
    today = gmt_today()

    '''
    flags = OperationFlags.retrieve()
    
    #Delay task if counters are being copied
    if not (flags.weekly_counter_copy and flags.monthly_counter_copy):
        enqueue_counter(payload_string,countdown = 60)
        return
    '''

    product_targets = defaultdict(int)
    user_targets = defaultdict(int)
    
    for payload in counter_targets:
      product_key = ProductCounter.build_key(payload.url, DAILY, today)
      user_key = UserCounter.build_key(payload.user_id, DAILY, today)
      product_targets[product_key] += 1
      user_targets[user_key] += 1
        
    product_counters = ProductCounter.get(product_targets.keys(),_result_type=DICT)
    user_counters = UserCounter.get(user_targets.keys(),_result_type=DICT)
        
    for key,delta in product_targets.iteritems():
      try:
        product_counters[key].count += delta
      except AttributeError: #Value is None in dict
        key_name = db.Key(key).name()
        store_key = Store.key_from_product_url(key_name)
        product_counters[key] = ProductCounter.new(key_name, DAILY, today,
                                                   count=delta,store = store_key,_build_key_name = False)

    for key,delta in user_targets.iteritems():  
      try:
        user_counters[key].count += delta
      except AttributeError: #Value is None in dict
        key_name = db.Key(key).name()
        user_counters[key] = UserCounter.new(key_name, DAILY, today,
                                             count=delta,_build_key_name = False)
                
    ProductCounter.filtered_update(product_counters.values())
    UserCounter.filtered_update(user_counters.values())

main, application = helipad.app({
    '/taskworker/bucket/': UrlBucketWorker,
    '/taskworker/url/': UrlFetchWorker,
    '/taskworker/counter/': CounterWorker,
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
