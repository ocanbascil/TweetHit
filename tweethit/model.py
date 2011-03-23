from PerformanceEngine import pdb
from google.appengine.ext import db
from tweethit.utils.parser_util import create_parser

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
    
    def __init__(self,url,user_id,store_url=None,asin=None):
        self['url'] = url
        self['user_id'] = user_id
        self['store_url'] = store_url
        self['asin'] = asin
            
    @property
    def url(self):
        return self['url']
    
    @property
    def user_id(self):
         return str(self['user_id'])
     
    @property 
    def store_url(self):
        return self['store_url']
    
    @property
    def asin(self):
        return self['asin']
     
    @classmethod
    def serialize(cls,array):
        return repr(array)
    
    @classmethod
    def deserialize(cls,string):
        arr = eval(string)
        result = []
        for item in arr:
            result.append(Payload(item['url'],
                                  item['user_id'],
                                  item['store_url'],
                                  item['asin']))
        return result