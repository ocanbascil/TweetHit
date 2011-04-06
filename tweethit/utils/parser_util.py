import re
import datetime

def str_to_date(string):
  if len(string):
    year,month,day = map(int,string.split('-'))
    return datetime.date(year,month,day)
  
def date_to_str_tuple(date):
  year,month,day = str(date).split('-')
  return year,month,day
   
class UrlParser(object):
  
  ROOT_URL_SET = []
  
  @classmethod
  def is_valid(cls,url):
    for item in cls.ROOT_URL_SET:
      if url.find(item,0,30):
        return True
    return False
    
  @classmethod
  def root_url(cls,url):
    if cls.is_valid(url):
      end_slash_index = url.find('/',7)
      if end_slash_index > 0:
        url = url[:end_slash_index]
      return url
    raise ParserException(ParserException.NO_PARSER_IMPLEMENTED+' :'+url)
   
  @classmethod
  def _remove_params(cls,url):
    param_index = url.find('?')
    if param_index != -1:
      return url[:param_index]
    else:
      return url
    
class AmazonURLParser(UrlParser):
  US_ROOT = 'http://www.amazon.com'
  UK_ROOT = 'http://www.amazon.co.uk'
  CA_ROOT = 'http://www.amazon.ca'
  DE_ROOT = 'http://www.amazon.de'
  IT_ROOT = 'http://www.amazon.it'
  JP_ROOT = 'http://www.amazon.co.jp'
  CN_ROOT = 'http://www.amazon.cn'
  FR_ROOT = 'http://www.amazon.fr'
  
  DEFAULT_PREFIX = '/o/ASIN/' #used for constructing urls
  ROOT_URL_SET = [US_ROOT,UK_ROOT,CA_ROOT,FR_ROOT,DE_ROOT,JP_ROOT]
  KEY_PREFIX_SET = ['/dp/','/gp/product/','/o/ASIN/','/exec/obidos/ASIN/']
  
  @classmethod
  def product_url(cls,url):
    return cls.root_url(url) + cls.DEFAULT_PREFIX + cls.extract_asin(url)

  @classmethod
  def get_locale(cls,url):
    root_url = cls.root_url(url)
    if root_url == cls.US_ROOT:
      return 'us'
    elif root_url == cls.UK_ROOT:
      return 'uk'
    elif root_url == cls.CA_ROOT:
      return 'ca'
    elif root_url == cls.DE_ROOT:
      return 'de'
    elif root_url == cls.FR_ROOT:
      return 'fr'
    elif root_url == cls.JP_ROOT:
      return 'jp'
    else:
      return None
            
  @classmethod
  def extract_asin(cls,url):  
    url = cls._remove_params(url)
    for prefix in cls.KEY_PREFIX_SET:
      prefix_index = url.find(prefix)
      if  prefix_index != -1:
        key_start_index = prefix_index + len(prefix)
      
        '''We expect an ideal url in the form 
        www.amazon.com/<key_prefix/<asin>/
        
        But sometimes % is used instead of /
        So we must check for that first
        www.amazon.com/<key_prefix>/<asin>%..
        '''
        percent_index = url.find('%',key_start_index)
        key_end_index = url.find('/',key_start_index)
        
        if key_end_index == -1:
            if percent_index == -1: #no more chars after the key
                key_end_index = len(url)
            else: #Trailing % in url
                key_end_index = percent_index
                
        result = url[key_start_index:key_end_index]
        '''Sometimes URL is in the form 
        amazon.com/dp/system-requirements/B0348023/...      
        So we check the next part if current one
        does not look like a valid ASIN
        '''
        while True:
          if re.match('([A-Z0-9])',result) is None:
            if key_end_index == -1:
              result = ''
              break
            key_start_index = key_end_index+1
            key_end_index = url.find('/',key_end_index+1)
            result = url[key_start_index:key_end_index]
          else:
            break
          
        if len(result):
          return result
    
    raise ParserException(url) #No matching key prefixes found    
       
class ParserException(Exception):

    EMPTY_URL = "empty url"
    NO_PARSER_IMPLEMENTED = "no parser implemented"

    def __init__(self, value):
        self.url = value
    def __str__(self):
        return repr(self.url)