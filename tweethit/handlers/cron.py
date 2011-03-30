import helipad
import logging
from config import *

from PerformanceEngine import pdb,DATASTORE,MEMCACHE

from tweethit.model import ProductCounter,UserCounter,ProductRenderer,\
CounterBase,DAILY,WEEKLY,MONTHLY,TwitterUser,Product,Banlist

from tweethit.query import USER_SPAM_COUNTERS,PRODUCT_RENDERER_BAN_TARGETS

from tweethit.utils.time_util import midnight_flag,gmt_today,gmt_yesterday
from tweethit.utils.task_util import enqueue_renderer_update,enqueue_cleanup
  
class CounterUpdate(helipad.Handler):
  '''Retrieves counters from memcache to update DB every 5 mins'''
  def get(self):
    counter_keys = CounterBase.get_cached_counter_keys()
    if not len(counter_keys):
      return
    logging.info('Counter keys retrieved: %s' %len(counter_keys))
    #Delete cached counter keys
    CounterBase.set_cached_counter_keys([])
    counters = CounterBase.get(counter_keys,_storage=MEMCACHE)    
    if len(counters):
      logging.info('Counters being inserted: %s' %len(counters))
      pdb.put(counters, _storage=DATASTORE)
    
class MinuteRating(helipad.Handler):
  '''Fetches  top product counters
  Updates product renderers if there's any
  
  Enqueues tasks to get product details from Amazon 
  if they're not listed already'''
  def get(self):
    enqueue_renderer_update(DAILY,gmt_today())
      
class DailyCleanup(helipad.Handler):
  def get(self):
    date = gmt_yesterday()
    enqueue_renderer_update(WEEKLY,date)
    enqueue_renderer_update(MONTHLY,date)
    enqueue_cleanup(UserCounter.kind(), DAILY, date)
    enqueue_cleanup(ProductCounter.kind(), DAILY, date)
    enqueue_cleanup(ProductRenderer.kind(), DAILY, date)
    enqueue_cleanup(ProductRenderer.kind(), WEEKLY, date,countdown = 3600)
    enqueue_cleanup(ProductRenderer.kind(), MONTHLY, date,countdown = 3600)
    
class WeeklyCleanup(helipad.Handler):
  def get(self):
    date = gmt_yesterday()
    enqueue_cleanup(ProductCounter.kind(), WEEKLY, date,countdown = 3600)
    
class MonthlyCleanup(helipad.Handler):
  def get(self):
    date = gmt_yesterday()
    enqueue_cleanup(ProductCounter.kind(), MONTHLY, date,countdown = 3600)
    
class ProductBanSynch(helipad.Handler):
  def get(self):
    renderers = PRODUCT_RENDERER_BAN_TARGETS.fetch(100)
    products = [Product(key_name = renderer.key_root) for renderer in renderers]
    product_counters = []
    for renderer in renderers:
      product_counters.append(ProductCounter(
                                             key_name = renderer.key().name(),
                                             is_banned = True,
                                             day = renderer.day,
                                             week = renderer.week,
                                             month = renderer.month,
                                             year = renderer.year))
      renderer.is_ban_synched = True
    
    targets = [product.key().name() for product in products]
    ban_list = Banlist.retrieve()
    ban_list.products += targets
    ban_list.put(_storage=[MEMCACHE,DATASTORE])     
    pdb.put(products+renderers+product_counters,_storage = [MEMCACHE,DATASTORE])
  
class BanSpammers(helipad.Handler):
  def get(self):
           
    USER_SPAM_COUNTERS.bind(spam_count_limit = SPAM_COUNT_LIMIT)
        
    user_counters = USER_SPAM_COUNTERS.fetch(100)
    users = []
    if len(user_counters):
      for counter in user_counters:
        counter.is_banned = True
        users.append(TwitterUser(key_name = counter.key_root))
      
      targets = [user.key().name() for user in users]
      ban_list = Banlist.retrieve()
      ban_list.users += targets
      ban_list.put(_storage=[MEMCACHE,DATASTORE])
      #TwitterUser.update_banlist([user.key().name() for user in users])
      logging.info('Banning users with keys: %s' %[user.key().name() for user in users])
      pdb.put(user_counters+users)
  
main, application = helipad.app({
  '/cron/updatecounters/': CounterUpdate,
  '/cron/rating/minute/': MinuteRating,
  '/cron/cleanup/day/': DailyCleanup,
  '/cron/cleanup/week/': WeeklyCleanup,
  '/cron/cleanup/month/': MonthlyCleanup,
  '/cron/bansynch/': ProductBanSynch,
  '/cron/banspammers/': BanSpammers,
})



if __name__ == '__main__':
    main()