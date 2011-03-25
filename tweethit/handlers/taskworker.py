import helipad
import logging

from google.appengine.ext.db import Key

from PerformanceEngine import LOCAL,MEMCACHE,DATASTORE, \
ALL_LEVELS,LIST,DICT,KEY_NAME_DICT,pdb

from tweethit.model import *
from tweethit.query import DAILY_TOP_COUNTERS

from tweethit.utils.parser_util import AmazonURLParser,ParserException
from tweethit.utils.rpc import UrlFetcher
from tweethit.utils.task_util import *
from tweethit.utils.time_util import gmt_today,str_to_date
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
      url_key =  str(Key.from_path('Url',payload.url))    
      cached_url = cached_urls[url_key]
      if cached_url is not None:
        if cached_url.is_product: #cached url points to a valid product page
          counter_targets.append(Payload(cached_url.product_url,
                                                      payload.user_id))
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
        product_url = AmazonURLParser.product_url(url.final_ur)
        user_id = url.user_id
        
        if product_url in product_ban_list:
            logging.info('Mention creation prevented for banned product url: %s' %product_url)
            continue #no action for banned product
        
        url.is_product = True #No exceptions for product_url => valid product reference
        
        counter_targets.append(Payload(product_url,user_id))
      except ParserException,e:
        pass
                       
    pdb.put(result_urls, _storage = [LOCAL,MEMCACHE]) #Urls are stored in cache only
    
    if len(counter_targets):
      counter_payload = Payload.serialize(counter_targets)
      enqueue_counter(counter_payload)
      
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
        
    product_counters = ProductCounter.get(product_targets.keys(),_result_type=KEY_NAME_DICT)
    user_counters = UserCounter.get(user_targets.keys(),_result_type=KEY_NAME_DICT)
        
    for key_name,delta in product_targets.iteritems():
      try:
        product_counters[key_name].count += delta
      except AttributeError: #Value is None in dict
        store_key = Store.key_from_product_url(key_name)
        product_counters[key_name] = ProductCounter.new(key_name, DAILY, today,
                                                   count=delta,store = store_key,_build_key_name = False)

    for key_name,delta in user_targets.iteritems():  
      try:
        user_counters[key_name].count += delta
      except AttributeError: #Value is None in dict
        user_counters[key_name] = UserCounter.new(key_name, DAILY, today,
                                             count=delta,_build_key_name = False)
                
    ProductCounter.filtered_update(product_counters.values())
    UserCounter.filtered_update(user_counters.values())
    
class ProductRendererUpdater(helipad.Handler):
    '''Create & update product renderers for given parameters
    params:
        - store_key_name : key name for store instance (http://www.amazon.com)
        - is_ranked : True / False (used for cleanup)
        - day_delta : This will be zero for today, -1 or else for computing past values
        - frequency : This will be the frequency property of created renderers 
    '''
    def post(self):
      import datetime
      store_key_name = self.request.get('store_key_name')
      date = str_to_date(self.request.get('date_string'))
      frequency = self.request.get('frequency')
      
      logging.info('Updating %s renderers for %s on %s' %(frequency,store_key_name,date))
        
      flags = OperationFlags.retrieve()
      delay_flag = False
      '''
      if frequency == MONTHLY and not flags.monthly_counter_copy:
        delay_flag = True
      elif frequency == WEEKLY and not flags.weekly_counter_copy:
        delay_flag = True
          
      if delay_flag:
        logging.info('Delaying creation of renderers for frequency: %s' %frequency)
        enqueue_renderer_update(frequency,day_delta,is_ranked,
                                countdown = 60,store_key_name = store_key_name)
        return
      '''
      
      store = Key.from_path('Store',store_key_name)
      
      renderers = []
  
      DAILY_TOP_COUNTERS.bind(store = store,day = date)
      
      product_counters = DAILY_TOP_COUNTERS.fetch(TEMPLATE_PRODUCT_COUNT)
      key_names = [counter.key().name() for counter in product_counters ]
      product_renderers = ProductRenderer.get_by_key_name(key_names,
                                                          _storage=[MEMCACHE,DATASTORE],_result_type=KEY_NAME_DICT)
      logging.info('product counters: %s' %product_counters)
      
      for counter in product_counters:
        renderer = product_renderers[counter.key().name()]
        try:
          renderer.count = counter.count
          renderers.append(renderer)
        except AttributeError: #Renderer is none
          
          enqueue_renderer_info(counter.key_root, 
                                        counter.count,
                                        date,
                                        frequency)
          '''
          enqueue_renderer_info(product_key_name,counter.count,
                                            date,frequency,is_ranked)
          '''
          logging.info('Enqueuing product info fetch for: %s' %counter.key().name())
          
      if len(renderers):
        logging.info('Inserting renderer array with length: %s' %len(renderers))
        pdb.put(renderers, _storage=[MEMCACHE,DATASTORE])

      flags.save()
'''
class ProductRendererInfoFetcher(helipad.Handler):
  #Retrieve information for a product to be displayed on web page
  def post(self):
    product_key_name = self.request.get('product_key_name')
    count = int(self.request.get('count'))
    retries = int(self.request.get('retries'))
    date_string = self.request.get('date') 
    frequency = self.request.get('frequency')
    
    logging.info('Fetching details for %s , frequency: %s' %(product_key_name,frequency))
    
    year,month,day = map(int,date_string.split('-'))
    date = datetime.date(year,month,day)
    
    product = Product(key_name = product_key_name)
    
    #Create empty renderer 
    renderer = ProductRenderer.new(product_key_name, date, frequency,count = count)
    
    renderer = AmazonProductFetcher.get_product_details(product.asin, renderer,product.locale)
    
    if renderer is not None: #If all details were fetched successfully
      renderer.new_put()
    else:
        
      if retries <  MAX_PRODUCT_INFO_RETRIES:
        retries += 1
        logging.error('Error saving product: %s, adding to queue again, retries: %s' %(product_key_name,retries))
        enqueue_renderer_info(product_key_name,count,date,frequency,
                                        is_ranked, countdown = 60, retries = retries)
      else:
        logging.critical('Max retries reached for product: %s' %product_key_name)
        renderer = ProductRenderer.new(product_key_name, date, frequency,count = count)
        renderer.is_banned = True
        renderer.log_properties()
        renderer.new_put()
'''
main, application = helipad.app({
    '/taskworker/bucket/': UrlBucketWorker,
    '/taskworker/url/': UrlFetchWorker,
    '/taskworker/counter/': CounterWorker,
    '/taskworker/rendererupdate/':ProductRendererUpdater,
    #'/taskworker/rendererinfo/':ProductRendererInfoFetcher,
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
