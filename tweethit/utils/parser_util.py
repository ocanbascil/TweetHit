import re

def extract_urls(text):
    
    url_list =re.findall("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",text)
    if len(url_list) == 0:
        return None
    
    return url_list



def create_parser(url):
    if url is None:
        raise ParserException(ParserException.EMPTY_URL)
    for key in AmazonTweetParser.ROOT_URL_SET:
        if url.find(key) != -1:
            return AmazonTweetParser(url)
    else:
        raise ParserException(ParserException.NO_PARSER_IMPLEMENTED+' :'+url)
   
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