import re
  
def create_parser(url):
    if url is None:
        raise ParserException(ParserException.EMPTY_URL)
    for key in AmazonTweetParser.ROOT_URL_SET:
        if url.find(key) != -1:
            return AmazonTweetParser(url)
    else:
        raise ParserException(ParserException.NO_PARSER_IMPLEMENTED+' :'+url)
   
class UrlParser(object):
  
  ROOT_URL_SET = []
  
  @classmethod
  def root_url(cls,url):
    for item in cls.ROOT_URL_SET:
      index = url.find(item)
      if index != -1:
        #find url ending slash, 7 = len(http://)
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
   
class AbstractTweetParser(object):
    KEY_PREFIX_SET = ''
    DEFAULT_PREFIX = ''
    
    def __init__(self,url):
        self.url = url
    
    def _remove_params(self):
        param_index = self.url.find('?')
        if param_index != -1:
            return self.url[:param_index]
        else:
            return self.url
    
    def extract_asin(self,clean_url):
        raise NotImplementedError("Subclasses are responsible for creating this method")
    
    @property
    def asin(self):
        clean_url = self._remove_params()
        return self.extract_asin(clean_url)
    
    @property    
    def product_url(self):
        return self.root_url + self.DEFAULT_PREFIX + self.asin
    
    @property
    def root_url(self):
        #find url ending slash, 7 = len(http://)
        end_slash_index = self.url.find('/',7)
        return self.url[:end_slash_index]
    
    @property
    def locale(self):
        raise NotImplementedError("Subclasses are responsible for creating this method")

class AmazonTweetParser(AbstractTweetParser):
    
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
        
    def extract_asin(self,clean_url):
        for prefix in self.KEY_PREFIX_SET:
            prefix_index = clean_url.find(prefix)
            if  prefix_index != -1:
                key_start_index = prefix_index + len(prefix)
                
                '''
                We expect an ideal url in the form 
                www.amazon.com/<key_prefix/<asin>/
                
                But sometimes % is used instead of /
                So we must check for that first
                www.amazon.com/<key_prefix>/<asin>%..
                '''
                percent_index = clean_url.find('%',key_start_index)
                key_end_index = clean_url.find('/',key_start_index)
                
                if key_end_index == -1:
                    if percent_index == -1: #no more chars after the key
                        key_end_index = len(clean_url)
                    else: #Trailing % in url
                        key_end_index = percent_index
                    
                result = clean_url[key_start_index:key_end_index]
                        
                #ASIN code check to prevent exceptions like
                #amazon.com/dp/system-requirements/B0348023/...        
                if re.match("([A-Z0-9])",result) is not None:        
                    return clean_url[key_start_index:key_end_index]
                
        raise ParserException(clean_url) #No matching key prefixes found
    
    #US_ROOT,UK_ROOT,CA_ROOT,IT_ROOT,FR_ROOT,DE_ROOT
    
    @property
    def locale(self):
        klass = self.__class__
        if self.root_url == klass.US_ROOT:
            return 'us'
        elif self.root_url == klass.UK_ROOT:
            return 'uk'
        elif self.root_url == klass.CA_ROOT:
            return 'ca'
        elif self.root_url == klass.DE_ROOT:
            return 'de'
        elif self.root_url == klass.FR_ROOT:
            return 'fr'
        elif self.root_url == klass.JP_ROOT:
            return 'jp'
        else:
            return None
        
    
class ParserException(Exception):

    EMPTY_URL = "empty url"
    NO_PARSER_IMPLEMENTED = "no parser implemented"

    def __init__(self, value):
        self.url = value
    def __str__(self):
        return repr(self.url)