from PerformanceEngine import pdb,MEMCACHE,DATASTORE

from google.appengine.ext import db
from google.appengine.api import memcache
from tweethit.utils.parser_util import create_parser,AmazonURLParser

import config

DAILY='daily'
WEEKLY='weekly'
MONTHLY='monthly'


class FrequencyBase(pdb.Model):
  '''Base model including methods for building key names 
  using date and frequency'''
  _valid_frequencies = set([DAILY,WEEKLY,MONTHLY])
  _default_delimiter = '|'
  
  day = db.DateProperty()
  week = db.IntegerProperty()
  month = db.IntegerProperty()
  year = db.IntegerProperty()
  
  @classmethod
  def frequency_from_key_name(cls,key_name):
    return key_name.split(cls._default_delimiter)[1]
  
  @property
  def key_root(self):
    klass = self.__class__
    return self.key().name().split(klass._default_delimiter)[0]
  
  @classmethod
  def build_key(cls,key_root,frequency,date):
    return db.Key.from_path(cls.kind(), 
                                    cls.build_key_name(key_root, frequency, date))
  
  @classmethod
  def build_key_name(cls,key_root,frequency,date):
    if frequency not in cls._valid_frequencies:
      raise FrequencyError(frequency)
    
    key_arr = [key_root,frequency]
    if frequency == DAILY:
      key_arr.append(date)
    elif frequency == WEEKLY:
      key_arr.extend([date.year,date.isocalendar()[1]])
    elif frequency == MONTHLY:
      key_arr.extend([date.year,date.month])
    
    key_arr = map(str,key_arr)
    return cls._default_delimiter.join(key_arr)
  
  @classmethod
  def new(cls,key_root,frequency,date,_build_key_name=True,**kwds):
    if _build_key_name:
      key_name = cls.build_key_name(key_root, frequency, date)
    else:
      key_name = key_root
      
    entity = cls(key_name=key_name,**kwds)
    
    if frequency == DAILY:
      entity.day=date
    elif frequency == WEEKLY:
      entity.week=date.isocalendar()[1]
      entity.year=date.year
    elif frequency == MONTHLY:
      entity.month = date.month
      entity.year = date.year
    
    return entity    

class FrequencyError(Exception):
  def __init__(self,param):
    self.type = type(param)
  def __str__(self):
    return  'Invalid frequency given for key name %s' %self.param

class OperationFlags(pdb.Model):
  '''Singleton container class that holds data for synching operation'''
  _key_name = 'OperationFlags'
  _storage = [MEMCACHE,DATASTORE]
  
  
  def save(self):
    self.put(_storage=self.__class__._storage)
    
  @classmethod
  def retrieve(cls):
      return cls.get_or_insert(cls._key_name, _storage=cls._storage)


class Store(pdb.Model):
    
  @classmethod
  def get_all_store_keys(cls):
    result = []
    for url in AmazonURLParser.ROOT_URL_SET:
      result.append(db.Key.from_path('Store',url))      
    return result
  
  @classmethod
  def key_from_product_url(cls,product_url):
    root = 'http://'+product_url.split('/')[2]
    return db.Key.from_path('Store',root)
        
  @classmethod
  def key_for_locale(cls,locale):
    root = 'http://www.amazon.'
    if locale == 'us':
      root += 'com'
    elif locale == 'uk':
      root += 'co.uk'
    elif locale == 'de':
      root += 'de'
    elif locale == 'ca':
      root += 'ca'
    elif locale == 'fr':
      root += 'fr'
    elif locale == 'jp':
      root += 'co.jp'
    else:
      raise StoreException('Store not found for locale: %s' %locale)
    
    return db.Key.from_path('Store',root)
            
class StoreException(Exception):
    
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)
       
class CounterBase(FrequencyBase):
  '''Base class for counters'''
  
  _MIN_COUNT_FOR_DB_WRITE = None #Must be overridden
  
  count = db.IntegerProperty(default = 0)
  #used for omitting spam,refreshed by cron
  is_banned = db.BooleanProperty(default = False)
  
  @classmethod
  def filtered_update(cls,models):
    db_targets = [str(model.key()) for model in models 
                        if model.count >= cls._MIN_COUNT_FOR_DB_WRITE]
    pdb.put(models,_storage=MEMCACHE)
    if len(db_targets):
        cls.update_cached_counter_keys(db_targets)

  @classmethod
  def update_cached_counter_keys(cls,key_array):
    '''Update counter_keys group in memcache for cron'''
    cached_keys = cls.get_cached_counter_keys()
    cached_keys = list(set(cached_keys + key_array))
    cls.set_cached_counter_keys(cached_keys)
      
  @classmethod
  def get_cached_counter_keys(cls):
    key_array = memcache.get('counter_keys')
    if key_array is None:
      key_array = []
      memcache.set('counter_keys',key_array)
        
    return key_array
  
  @classmethod
  def set_cached_counter_keys(cls,arr):
    memcache.set('counter_keys',arr)
    
class UserCounter(CounterBase):
    '''Counter class that holds the mention counts for a twitter user
    This is  used for finding out spam & promotion accounts and ban them'''
    _MIN_COUNT_FOR_DB_WRITE = config.USER_COUNTER_MIN_COUNT

class StoreFrequencyBase(FrequencyBase):
  store = db.ReferenceProperty()
  
  @classmethod
  def new(cls,*args,**kwds):
    entity = super(StoreFrequencyBase, cls).new(*args,**kwds)
    store_key_name = AmazonURLParser.root_url(args[0])
    entity.store = db.Key.from_path('Store',store_key_name)
    return entity

class ProductCounter(CounterBase,StoreFrequencyBase):
  '''Counter class that holds the number of mentions for a product, daily,weekly, monthly and yearly'''
  _MIN_COUNT_FOR_DB_WRITE = config.PRODUCT_COUNTER_MIN_COUNT
      
class ProductRenderer(StoreFrequencyBase):
  '''Data model for holding product information
  Includes data from Product,ProductCounter,Amazon Products API
  Model must be unique for date & url properties => Parent =  product, key_name = current date
  
  Do not do any logic operations using this class
  This is used for creating views only
  '''
    
  @classmethod
  def new(cls,*args,**kwds):
    entity = super(ProductRenderer, cls).new(*args,**kwds)
    url = AmazonURLParser.product_url(args[0])
    entity.url = url
    return entity
  
  #store = db.ReferenceProperty(Store)
  #product = db.ReferenceProperty(Product)
  is_banned = db.BooleanProperty(default = False)
  is_ban_synched = db.BooleanProperty(default = False)
      
  url = db.LinkProperty(indexed = False)
  
  #Amazon Product API
  image_small = db.LinkProperty(indexed=False)
  image_medium = db.LinkProperty(indexed=False)
  image_large = db.LinkProperty(indexed=False)
  price = db.StringProperty(indexed=False) #price + currency representation
  product_group = db.StringProperty(indexed=False)
  title = db.StringProperty(indexed=False)
  rating = db.FloatProperty(indexed = False,default = 0.0)
  
  #ProductCounter
  count = db.IntegerProperty(default = 0)


class Url(pdb.Model):
  '''This model is used for storing shortened - final url tuples
  If final url is a valid Amazon Product page then the url is set as valid
  key_name = short_url
  '''
  add_date = db.DateProperty(auto_now_add = True)
  final_url = db.LinkProperty(indexed=False)
  user_id = db.StringProperty(indexed = False) #Used for creating counter payloads in bucket worker
  is_valid = db.BooleanProperty(default = False) #Has a final url that has been fetched successfully
  is_product = db.BooleanProperty(default = False) #Final url points to a valid Amazon Product page
  
  @property
  def parser(self):
    if not hasattr(self, '_parser'):
      self._parser = create_parser(self.final_url)
    return self._parser
  
  @property
  def asin(self):
    return self.parser.asin
  
  @property 
  def product_url(self):
    return self.parser.product_url
    
  @property
  def root_url(self):
    return self.parser.root_url
      
class Payload(dict):
  '''This class is serialized and passed along taskworkers as message body'''
  
  def __init__(self,url,user_id):
    self['url'] = url
    self['user_id'] = user_id
          
  @property
  def url(self):
    return self['url']
  
  @property
  def user_id(self):
    return str(self['user_id'])
      
  @classmethod
  def serialize(cls,array):
      return repr(array)
  
  @classmethod
  def deserialize(cls,string):
    arr = eval(string)
    result = []
    for item in arr:
        result.append(Payload(item['url'],
                              item['user_id']))
    return result