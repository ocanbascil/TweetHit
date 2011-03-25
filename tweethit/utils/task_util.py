from tweethit.utils.parser_util import AmazonTweetParser
from google.appengine.api import taskqueue
import time
import logging

productinfo_queue = taskqueue.Queue('productinfo')
cleanup_queue = taskqueue.Queue('cleanup')
url_queue = taskqueue.Queue('url')
fast_queue = taskqueue.Queue('fastqueue')

def prevent_transient_error(fn):
  def keep_trying(*args,**kwargs):
    timeout_ms = 100
    while True:      
      try:
        return fn(*args,**kwargs)    
      except taskqueue.TransientError:
        time.sleep(timeout_ms)
        timeout_ms *= 2
  return keep_trying

@prevent_transient_error
def enqueue_url_fetch(payload):
    t = taskqueue.Task(url='/taskworker/url/', 
                      params={'payload': payload})
    url_queue.add(t)
    
@prevent_transient_error
def enqueue_counter(payload,countdown = 0):
    t = taskqueue.Task(url='/taskworker/counter/', 
                       countdown = countdown,
                       params={'payload': payload})
    
    fast_queue.add(t)
    
@prevent_transient_error
def enqueue_counter_copy(source_frequency,target_frequency,day_delta):
    t = taskqueue.Task(url='/taskworker/countercopy/', 
                  params={'source_frequency': source_frequency,
                           'target_frequency':target_frequency,
                           'day_delta':day_delta})
    
    fast_queue.add(t)

@prevent_transient_error
def enqueue_cleanup(model_kind, frequency = '',cache_cleanup = False, countdown = 0):
    t = taskqueue.Task(url='/taskworker/cleanup/', 
                  countdown = countdown,
                  params={'model_kind': model_kind,
                           'frequency':frequency,
                           'cache_cleanup':cache_cleanup})
    
    cleanup_queue.add(t)
    
@prevent_transient_error
def enqueue_renderer_update(frequency,date, countdown = 0,store_key_name = None):
        if store_key_name:
            store_group = [store_key_name]
        else:
            store_group = AmazonTweetParser.ROOT_URL_SET
    
        for root_url in store_group:
            t = taskqueue.Task(url='/taskworker/rendererupdate/',
                               countdown = countdown, 
                              params={'store_key_name': root_url,
                                        'frequency':frequency,
                                        'date_string':str(date)})
            fast_queue.add(t)
            countdown += 1 #Just in case they all start to write operation flags at once
   
@prevent_transient_error     
def enqueue_renderer_info(product_key_name,count,frequency,date,
                                        countdown = 0,retries = 0):

    t = taskqueue.Task(url='/taskworker/rendererinfo/', 
                       countdown = countdown,
                       params={'product_key_name': product_key_name,
                                'count':count,
                                'date_string':str(date),
                                'frequency': frequency,
                                'retries' : retries,})
    productinfo_queue.add(t)
      
    